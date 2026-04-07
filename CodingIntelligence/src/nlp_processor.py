"""
NLP Processor
Handles IMO Entity Extraction API and Precision Normalize API integration
"""
import requests
import json
import uuid
import csv
import os
import glob
from typing import Dict, List, Any
import config


class NLPProcessor:
    """
    Process medical text using IMO Health APIs for entity extraction and normalization.
    """
    
    def __init__(self):
        """Initialize the NLP processor with IMO API credentials."""
        self.auth_url = config.imo_auth_url if hasattr(config, 'imo_auth_url') else "https://api.imohealth.com/oauth/token"
        self.entity_extraction_url = config.imo_entity_extraction_url if hasattr(config, 'imo_entity_extraction_url') else "https://api.imohealth.com/entityextraction/pipelines/imo-clinical-comprehensive"
        self.normalize_enrichment_url = config.imo_precision_normalize_enrichment_url if hasattr(config, 'imo_precision_normalize_enrichment_url') else "https://api.imohealth.com/precision/normalize/enrichment"
        self.normalize_url = config.imo_precision_normalize_url if hasattr(config, 'imo_precision_normalize_url') else "https://api.imohealth.com/precision/normalize"
        self.coding_intelligence_url = config.imo_coding_intelligence_url if hasattr(config, 'imo_coding_intelligence_url') else "https://api.imohealth.com/codingintelligence/v1/rules/imo-admin-coding-sets"
        self.coding_intelligence_excludes1_url = config.imo_coding_intelligence_excludes1_url if hasattr(config, 'imo_coding_intelligence_excludes1_url') else "https://api.imohealth.com/codingintelligence/v1/rules/cms-excludes1"
        
        # Get API credentials from config
        try:
            self.client_id = config.imo_client_id
            self.client_secret = config.imo_client_secret
            self.access_token = None
            self.token_expiry = None
            
            # Diagnostic workflow credentials
            self.workflow_client_id = config.imo_diagnostic_workflow_client_id if hasattr(config, 'imo_diagnostic_workflow_client_id') else None
            self.workflow_client_secret = config.imo_diagnostic_workflow_client_secret if hasattr(config, 'imo_diagnostic_workflow_client_secret') else None
            self.workflow_access_token = None
            self.workflow_token_expiry = None
            
            # Coding Intelligence credentials
            self.coding_intel_client_id = config.imo_coding_intelligence_client_id if hasattr(config, 'imo_coding_intelligence_client_id') else None
            self.coding_intel_client_secret = config.imo_coding_intelligence_client_secret if hasattr(config, 'imo_coding_intelligence_client_secret') else None
            self.coding_intel_access_token = None
            self.coding_intel_token_expiry = None
        except AttributeError:
            print("Warning: IMO API credentials not found in config. Using demo mode.")
            self.client_id = None
            self.client_secret = None
            self.access_token = None
            self.token_expiry = None
            self.workflow_client_id = None
            self.workflow_client_secret = None
            self.workflow_access_token = None
            self.workflow_token_expiry = None
            self.coding_intel_client_id = None
            self.coding_intel_client_secret = None
            self.coding_intel_access_token = None
            self.coding_intel_token_expiry = None
        
        # Load CPT to HCPCS/ICD10PCS mapping from Rules folder
        self.cpt_code_mapping = self._load_cpt_code_mapping()
    
    def _load_cpt_code_mapping(self) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Load CPT to HCPCS and ICD-10-PCS code mappings from Rules CSV files.
        
        Returns:
            dict: Mapping of CPT codes to associated HCPCS and ICD-10-PCS codes
                  Format: {
                      'CPT_CODE': {
                          'HCPCS': [{'code': 'C1884', 'description': '...'}],
                          'ICD10PCS': [{'code': '037J3DZ', 'description': '...'}]
                      }
                  }
        """
        mapping = {}
        rules_folder = os.path.join('sample_data', 'Rules')
        
        if not os.path.exists(rules_folder):
            return mapping
        
        # Find all CSV files in Rules folder
        csv_files = glob.glob(os.path.join(rules_folder, '*.csv'))
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    
                    # Group codes by value set
                    current_value_set_codes = {
                        'CPT': [],
                        'HCPCS': [],
                        'ICD10PCS': []
                    }
                    
                    for row in reader:
                        code_system = row.get('Code system', '').strip()
                        code = row.get('Code', '').strip()
                        description = row.get('Description', '').strip()
                        
                        # Normalize code system names
                        if 'CPT' in code_system.upper():
                            current_value_set_codes['CPT'].append({
                                'code': code,
                                'description': description
                            })
                        elif 'HCPCS' in code_system.upper():
                            current_value_set_codes['HCPCS'].append({
                                'code': code,
                                'description': description
                            })
                        elif 'ICD-10-PCS' in code_system.upper() or 'ICD10PCS' in code_system.upper():
                            current_value_set_codes['ICD10PCS'].append({
                                'code': code,
                                'description': description
                            })
                    
                    # Create mapping: for each CPT code, associate all HCPCS and ICD10PCS codes
                    for cpt_entry in current_value_set_codes['CPT']:
                        cpt_code = cpt_entry['code']
                        if cpt_code not in mapping:
                            mapping[cpt_code] = {
                                'HCPCS': [],
                                'ICD10PCS': []
                            }
                        
                        # Add all HCPCS codes from this value set
                        mapping[cpt_code]['HCPCS'].extend(current_value_set_codes['HCPCS'])
                        # Add all ICD10PCS codes from this value set
                        mapping[cpt_code]['ICD10PCS'].extend(current_value_set_codes['ICD10PCS'])
                
            except Exception as e:
                pass
        
        return mapping
    
    def _enrich_codemaps_with_associated_codes(self, codemaps: Dict) -> Dict:
        """
        Enrich entity codemaps with associated HCPCS and ICD-10-PCS codes based on CPT codes.
        
        Args:
            codemaps (dict): Original codemaps from entity extraction
            
        Returns:
            dict: Enriched codemaps with associated codes
        """
        if not codemaps or not self.cpt_code_mapping:
            return codemaps
        
        # Check if entity has CPT codes
        if 'CPT' in codemaps or 'cpt' in codemaps:
            cpt_data = codemaps.get('CPT') or codemaps.get('cpt') or {}
            
            # Extract CPT codes
            cpt_codes = []
            if 'codes' in cpt_data and isinstance(cpt_data['codes'], list):
                cpt_codes = [c.get('code', '') for c in cpt_data['codes']]
            elif 'code' in cpt_data:
                cpt_codes = [cpt_data['code']]
            
            # Look up associated codes for each CPT code
            for cpt_code in cpt_codes:
                    
                    # Add HCPCS codes if found
                    if associated_codes['HCPCS']:
                        if 'HCPCS' not in codemaps:
                            codemaps['HCPCS'] = {'codes': []}
                        
                        # Add associated HCPCS codes
                        for hcpcs_entry in associated_codes['HCPCS']:
                            # Check if code already exists
                            existing_codes = [c.get('code', '') for c in codemaps.get('HCPCS', {}).get('codes', [])]
                            if hcpcs_entry['code'] not in existing_codes:
                                codemaps['HCPCS']['codes'].append({
                                    'code': hcpcs_entry['code'],
                                    'title': hcpcs_entry['description'],
                                    'source': 'Rules-based enrichment (Associated with CPT)'
                                })
                    
                    # Add ICD-10-PCS codes if found and not already present
                    if associated_codes['ICD10PCS']:
                        if 'ICD10PCS' not in codemaps:
                            codemaps['ICD10PCS'] = {'codes': []}
                        
                        # Add associated ICD-10-PCS codes
                        for icd10pcs_entry in associated_codes['ICD10PCS']:
                            # Check if code already exists
                            existing_codes = [c.get('code', '') for c in codemaps.get('ICD10PCS', {}).get('codes', [])]
                            if icd10pcs_entry['code'] not in existing_codes:
                                codemaps['ICD10PCS']['codes'].append({
                                    'code': icd10pcs_entry['code'],
                                    'title': icd10pcs_entry['description'],
                                    'source': 'Rules-based enrichment (Associated with CPT)'
                                })
        
        return codemaps
    
    def _get_access_token(self) -> str:
        """
        Get OAuth access token from IMO auth endpoint.
        
        Returns:
            str: Access token
        """
        import time
        
        # Check if we have a valid token
        if self.access_token and self.token_expiry and time.time() < self.token_expiry:
            return self.access_token
        
        print("Getting new access token from IMO OAuth endpoint...")
        
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            
            payload = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'audience': 'https://api.imohealth.com'
            }
            
            response = requests.post(
                self.auth_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')
                expires_in = result.get('expires_in', 3600)
                self.token_expiry = time.time() + expires_in - 60  # Refresh 60s before expiry
                print(f"✓ Access token obtained (expires in {expires_in}s)")
                return self.access_token
            else:
                print(f"✗ OAuth Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error getting access token: {str(e)}")
            return None
    
    def _get_diagnostic_workflow_token(self) -> str:
        """
        Get OAuth access token for diagnostic workflow endpoint.
        Uses separate credentials from the main API.
        
        Returns:
            str: Access token for diagnostic workflow
        """
        import time
        
        # Check if we have a valid token
        if self.workflow_access_token and self.workflow_token_expiry and time.time() < self.workflow_token_expiry:
            return self.workflow_access_token
        
        print("Getting new diagnostic workflow access token from IMO OAuth endpoint...")
        
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            
            payload = {
                'grant_type': 'client_credentials',
                'client_id': self.workflow_client_id,
                'client_secret': self.workflow_client_secret,
                'audience': 'https://api.imohealth.com'
            }
            
            response = requests.post(
                self.auth_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.workflow_access_token = result.get('access_token')
                expires_in = result.get('expires_in', 3600)
                self.workflow_token_expiry = time.time() + expires_in - 60  # Refresh 60s before expiry
                print(f"✓ Diagnostic workflow access token obtained (expires in {expires_in}s)")
                return self.workflow_access_token
            else:
                print(f"✗ Diagnostic Workflow OAuth Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error getting diagnostic workflow access token: {str(e)}")
            return None
    
    def extract_entities(self, text: str) -> Dict[str, List[Dict]]:
        """
        Extract entities from medical text using IMO Entity Extraction API.
        
        Args:
            text (str): Medical text (Assessment and Plan sections)
            
        Returns:
            dict: Extracted entities categorized by type (problems, procedures, medications, labs)
        """
        if not text:
            return {
                'problems': [],
                'procedures': [],
                'medications': [],
                'labs': []
            }
        
        print(f"Extracting entities from text: {len(text)} characters")
        
        # If no API credentials, use demo extraction
        if not self.client_id or not self.client_secret:
            print("No API credentials found, using demo mode")
            return self._demo_extract_entities(text)
        
        try:
            # Get OAuth access token
            access_token = self._get_access_token()
            if not access_token:
                print("Could not obtain access token, using demo mode")
                return self._demo_extract_entities(text)
            
            # Prepare API request
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            payload = {
                'text': text
            }
            
            # Call IMO Entity Extraction API
            print(f"Calling IMO Entity Extraction API: {self.entity_extraction_url}")
            response = requests.post(
                self.entity_extraction_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Successfully extracted entities from API")

                return self._parse_extraction_response(result, text)
            else:
                print(f"✗ API Error: {response.status_code} - {response.text}")
                return self._demo_extract_entities(text)
                
        except Exception as e:
            print(f"Error calling Entity Extraction API: {str(e)}")
            return self._demo_extract_entities(text)
    
    def _parse_extraction_response(self, response: Dict, original_text: str = "") -> Dict[str, List[Dict]]:
        """
        Parse IMO Entity Extraction API response.
        
        Args:
            response (dict): API response
            original_text (str): Original text for context extraction
            
        Returns:
            dict: Categorized entities with context
        """
        entities = {
            'problems': [],
            'procedures': [],
            'medications': [],
            'labs': []
        }
        
        # Parse entities from response
        if 'entities' in response:
            print(f"Parsing {len(response['entities'])} entities from response")
            
            # Define entities to ignore (generic/administrative terms)
            ignore_patterns = [
                'review test results', 'patient education', 'lifestyle', 
                'education', 'review', 'follow-up', 'follow up',
                'appointment', 'monitoring', 'discussion', 'counseling',
                'instructions', 'recommendations', 'assessment', 'plan'
            ]
            
            for entity in response['entities']:
                # Only include entities with assertion "present"
                assertion = entity.get('assertion', '').lower()
                if assertion != 'present':
                    print(f"Skipping entity '{entity.get('text', '')}' with assertion '{assertion}'")
                    continue
                
                # Check if entity text matches ignore patterns
                entity_text = entity.get('text', '').lower().strip()
                if any(pattern in entity_text for pattern in ignore_patterns):
                    print(f"Ignoring generic entity: '{entity.get('text', '')}'")
                    continue
                
                category = entity.get('semantic', '').lower()
                offset = entity.get('begin', 0)
                end_offset = entity.get('end', 0)
                length = end_offset - offset
                
                # Extract context around the entity (200 chars before and after for context)
                context = self._extract_context(original_text, offset, length, context_window=200)
                
                # Extract codes from codemaps
                imo_code = ''
                imo_description = ''
                code_system = 'IMO'
                confidence = 0.0
                
                if 'codemaps' in entity and 'imo' in entity['codemaps']:
                    imo_data = entity['codemaps']['imo']
                    imo_code = imo_data.get('lexical_code', '')
                    imo_description = imo_data.get('lexical_title', '')
                    confidence = float(imo_data.get('confidence', 0.0))
                
                # Enrich codemaps with associated HCPCS/ICD-10-PCS codes based on CPT codes
                enriched_codemaps = self._enrich_codemaps_with_associated_codes(entity.get('codemaps', {}))
                
                entity_data = {
                    'text': entity.get('text', ''),
                    'code': imo_code,
                    'code_system': code_system,
                    'description': imo_description,
                    'offset': offset,
                    'length': length,
                    'confidence': confidence,
                    'context': context,
                    'entity_id': entity.get('id', ''),
                    'semantic': entity.get('semantic', ''),
                    'assertion': entity.get('assertion', ''),
                    'codemaps': enriched_codemaps
                }
                
                # Map categories
                if 'problem' in category or 'condition' in category or 'diagnosis' in category:
                    entities['problems'].append(entity_data)
                elif 'procedure' in category:
                    entities['procedures'].append(entity_data)
                elif 'medication' in category or 'drug' in category:
                    entities['medications'].append(entity_data)
                elif 'lab' in category or 'observation' in category or 'test' in category:
                    entities['labs'].append(entity_data)
        
        # Deduplicate entities by IMO lexical code
        entities = self._deduplicate_entities(entities)
        
        # Log enriched procedures with associated HCPCS codes
        print("\nChecking for CPT-to-HCPCS enrichments...")
        for entity in entities.get('procedures', []):
            codemaps = entity.get('codemaps', {})
            if 'HCPCS' in codemaps and codemaps['HCPCS'].get('codes'):
                hcpcs_codes = codemaps['HCPCS']['codes']
                enriched_codes = [c for c in hcpcs_codes if c.get('source') == 'Rules-based enrichment (Associated with CPT)']
                if enriched_codes:
                    print(f"  ✓ Added {len(enriched_codes)} associated HCPCS code(s) for: {entity.get('text', '')}")
                    for code in enriched_codes:
                        print(f"    - HCPCS {code.get('code', '')} ({code.get('title', '')})")
        
        # Enrich problems with MCC/CC flags
        print("\nEnriching problems with MCC/CC flags...")
        for entity in entities.get('problems', []):
            imo_code = entity.get('code', '')
            if imo_code and imo_code != 'N/A':
                flags = self._get_mcc_cc_flags(imo_code)
                entity['mcc_flag'] = flags.get('mcc_flag', 'N/A')
                entity['cc_flag'] = flags.get('cc_flag', 'N/A')
                
                # Log flags if present
                if flags.get('mcc_flag') == '1':
                    print(f"  ✓ MCC flag found for: {entity.get('text', '')} (IMO: {imo_code})")
                elif flags.get('cc_flag') == '1':
                    print(f"  ✓ CC flag found for: {entity.get('text', '')} (IMO: {imo_code})")
            else:
                entity['mcc_flag'] = 'N/A'
                entity['cc_flag'] = 'N/A'
        
        return entities
    
    def _deduplicate_entities(self, entities: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Deduplicate entities with the same IMO lexical code within each category.
        Keeps the first occurrence and merges contexts from duplicates.
        
        Args:
            entities (dict): Categorized entities
            
        Returns:
            dict: Deduplicated entities
        """
        deduplicated = {}
        
        for category, entity_list in entities.items():
            seen_codes = {}
            unique_entities = []
            
            for entity in entity_list:
                # Get IMO lexical code
                imo_code = entity.get('code', '')
                
                if not imo_code or imo_code == 'N/A':
                    # If no IMO code, keep the entity as unique
                    unique_entities.append(entity)
                    continue
                
                # Check if we've seen this IMO code before
                if imo_code in seen_codes:
                    # Merge context from duplicate
                    existing_entity = seen_codes[imo_code]
                    existing_context = existing_entity.get('context', '')
                    new_context = entity.get('context', '')
                    
                    # Only merge if contexts are different
                    if new_context and new_context not in existing_context:
                        merged_context = f"{existing_context} ... {new_context}"
                        existing_entity['context'] = merged_context
                    
                    print(f"Deduplicating: '{entity.get('text', '')}' (IMO: {imo_code})")
                else:
                    # First occurrence of this IMO code
                    seen_codes[imo_code] = entity
                    unique_entities.append(entity)
            
            deduplicated[category] = unique_entities
            
            # Log deduplication stats
            if len(entity_list) > len(unique_entities):
                duplicates_removed = len(entity_list) - len(unique_entities)
                print(f"Removed {duplicates_removed} duplicate(s) from {category}")
        
        return deduplicated
    
    def _get_mcc_cc_flags(self, imo_lexical_code: str) -> Dict[str, str]:
        """
        Get MCC (Major Complication/Comorbidity) and CC (Complication/Comorbidity) flags
        for a given IMO lexical code using IMO Core Search API.
        
        Args:
            imo_lexical_code (str): IMO lexical code
            
        Returns:
            dict: Dictionary with 'mcc_flag' and 'cc_flag' keys (values: '0', '1', or 'N/A')
        """
        if not imo_lexical_code or imo_lexical_code == 'N/A':
            return {'mcc_flag': 'N/A', 'cc_flag': 'N/A'}
        
        # Get diagnostic workflow access token (Core Search API requires workflow credentials)
        access_token = self._get_diagnostic_workflow_token()
        if not access_token:
            print(f"Failed to get diagnostic workflow access token for Core Search API")
            return {'mcc_flag': 'N/A', 'cc_flag': 'N/A'}
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            payload = {
                "usePreviousVersion": False,
                "sessionId": "00000000-0000-0000-0000-000000000000",
                "codes": [imo_lexical_code],
                "payloadIndex": 1,
                "paths": [],
                "properties": [],
                "clientApp": "RevecoreAccelerator",
                "clientAppVersion": "1.0",
                "siteId": "HospitalA",
                "userId": "UserA",
                "metadata": {
                    "encounterId": "12345"
                }
            }
            
            # Core Search API endpoint
            core_search_url = 'https://api.imohealth.com/core/search/v2/product/ProblemIT_Professional/item'
            
            response = requests.post(
                core_search_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract flags from response based on ItemResponse schema
                if 'ItemResponse' in result and 'items' in result['ItemResponse']:
                    items = result['ItemResponse']['items']
                    if len(items) > 0:
                        item = items[0]
                        mcc_flag = str(item.get('MCC_FLAG', '0'))
                        cc_flag = str(item.get('CC_FLAG', '0'))
                        
                        # Log the flags
                        if mcc_flag == '1':
                            print(f"  ✓ MCC flag: {mcc_flag} for code {imo_lexical_code} - {item.get('title', '')}")
                        elif cc_flag == '1':
                            print(f"  ✓ CC flag: {cc_flag} for code {imo_lexical_code} - {item.get('title', '')}")
                        
                        return {
                            'mcc_flag': mcc_flag,
                            'cc_flag': cc_flag
                        }
                    else:
                        return {'mcc_flag': '0', 'cc_flag': '0'}
                else:
                    return {'mcc_flag': '0', 'cc_flag': '0'}
            else:
                error_msg = f"Core Search API Error for code {imo_lexical_code}: {response.status_code}"
                try:
                    error_detail = response.json()
                    print(f"{error_msg} - {error_detail}")
                except:
                    print(f"{error_msg} - {response.text}")
                return {'mcc_flag': 'N/A', 'cc_flag': 'N/A'}
                
        except Exception as e:
            print(f"Error getting MCC/CC flags for code {imo_lexical_code}: {str(e)}")
            return {'mcc_flag': 'N/A', 'cc_flag': 'N/A'}
    
    def _get_coding_intelligence_token(self) -> str:
        """
        Get OAuth access token for Coding Intelligence API.
        Uses separate credentials from the main API.
        
        Returns:
            str: Access token for coding intelligence
        """
        import time
        
        # Check if we have a valid token
        if self.coding_intel_access_token and self.coding_intel_token_expiry and time.time() < self.coding_intel_token_expiry:
            return self.coding_intel_access_token
        
        print("Getting new coding intelligence access token from IMO OAuth endpoint...")
        
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            
            payload = {
                'grant_type': 'client_credentials',
                'client_id': self.coding_intel_client_id,
                'client_secret': self.coding_intel_client_secret,
                'audience': 'https://api.imohealth.com'
            }
            
            response = requests.post(
                self.auth_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.coding_intel_access_token = result.get('access_token')
                expires_in = result.get('expires_in', 3600)
                self.coding_intel_token_expiry = time.time() + expires_in - 60  # Refresh 60s before expiry
                print(f"✓ Coding intelligence access token obtained (expires in {expires_in}s)")
                return self.coding_intel_access_token
            else:
                print(f"✗ Coding Intelligence OAuth Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error getting coding intelligence access token: {str(e)}")
            return None
    
    def validate_billing_codes(self, codes: List[Dict[str, str]]) -> List[Dict]:
        """
        Validate ICD-10-CM codes for billing appropriateness using IMO Coding Intelligence API.
        
        Args:
            codes (list): List of dicts with 'code' and 'code_system' keys
            
        Returns:
            list: List of validation results with warnings/errors
        """
        if not codes:
            return []
        
        # Get coding intelligence access token
        access_token = self._get_coding_intelligence_token()
        if not access_token:
            print("Failed to get access token for Coding Intelligence API")
            return []
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            # Prepare payload with all value_set_ids
            payload = {
                "library_title": "IMO Precision Administrative Coding Assistance Sets",
                "category_titles": [],
                "value_set_ids": [
                    8054, 11248, 11247, 8057, 10098, 10090, 10095, 10093, 
                    10094, 10096, 10101, 10087, 10092, 10089, 10102, 10088, 
                    10097, 10099
                ],
                "codes": codes
            }
            
            print(f"Validating {len(codes)} codes with Coding Intelligence API...")
            
            response = requests.post(
                self.coding_intelligence_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                validated_codes = result.get('codes', [])
                
                # Log issues found with detailed messages
                issues_count = 0
                for code_result in validated_codes:
                    if code_result.get('is_nonprimary') or code_result.get('is_unspecified'):
                        issues_count += 1
                        code = code_result.get('code', 'Unknown')
                        description = code_result.get('description', 'No description')
                        message = code_result.get('message_text', 'No message provided')
                        
                        flags = []
                        if code_result.get('is_nonprimary'):
                            flags.append('NON-PRIMARY')
                        if code_result.get('is_unspecified'):
                            flags.append('UNSPECIFIED')
                        
                        print(f"  ⚠️  {code} - {description}")
                        print(f"      Flags: {', '.join(flags)}")
                        print(f"      Reason: {message}")
                        print()
                
                if issues_count > 0:
                    print(f"✓ Validation complete: {issues_count} code(s) with billing issues found")
                else:
                    print(f"✓ Validation complete: All codes are appropriate for billing")
                
                return validated_codes
            else:
                print(f"✗ Coding Intelligence API Error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Error calling Coding Intelligence API: {str(e)}")
            return []
    
    def check_excludes1_conflicts(self, codes: List[Dict[str, str]]) -> List[Dict]:
        """
        Check ICD-10-CM codes for CMS Excludes1 conflicts using IMO Coding Intelligence API.
        Two diagnosis codes that conflict under Excludes1 cannot be documented together.

        Args:
            codes (list): List of dicts with 'code' and 'code_system' keys

        Returns:
            list: AnalysisResult objects; each has 'code', 'note_codes' (conflicting codes)
        """
        if not codes:
            return []

        access_token = self._get_coding_intelligence_token()
        if not access_token:
            print("Failed to get access token for Coding Intelligence Excludes1 API")
            return []

        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }

            # Spec requires code, code_system, and record_id on each CodeInput
            payload = {
                "codes": [
                    {
                        "code": c.get('code', ''),
                        "code_system": c.get('code_system', 'ICD-10-CM'),
                        "record_id": str(i + 1)
                    }
                    for i, c in enumerate(codes)
                    if c.get('code')
                ]
            }

            if not payload['codes']:
                return []

            print(f"Checking {len(payload['codes'])} codes for Excludes1 conflicts...")

            response = requests.post(
                self.coding_intelligence_excludes1_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                total = data.get('total_results', 0)
                print(f"✓ Excludes1 check complete: {total} result(s) returned")
                # Log any conflicts found
                for r in results:
                    note_codes = r.get('note_codes', [])
                    if note_codes:
                        conflicting = [nc.get('code') for nc in note_codes]
                        print(f"  ⚠️  Excludes1 conflict: {r.get('code')} conflicts with {conflicting}")
                return results
            else:
                print(f"✗ Excludes1 API Error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            print(f"Error calling Excludes1 API: {str(e)}")
            return []

    def _extract_context(self, text: str, offset: int, length: int, context_window: int = 1000) -> str:
        """
        Extract context around an entity in the text.
        
        Args:
            text (str): Full text
            offset (int): Starting position of entity
            length (int): Length of entity
            context_window (int): Number of characters before/after to include
            
        Returns:
            str: Context string with entity highlighted
        """
        if not text:
            return ""
        
        start = max(0, offset - context_window)
        end = min(len(text), offset + length + context_window)
        
        context = text[start:end].strip()
        
        # Add ellipsis if context is truncated
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."
        
        return context
    
    def _demo_extract_entities(self, text: str) -> Dict[str, List[Dict]]:
        """
        Demo entity extraction using keyword matching (fallback when API not available).
        
        Args:
            text (str): Medical text
            
        Returns:
            dict: Extracted entities
        """
        entities = {
            'problems': [],
            'procedures': [],
            'medications': [],
            'labs': []
        }
        
        text_lower = text.lower()
        
        # Common medical terms for demo
        problem_keywords = [
            'hypertension', 'diabetes', 'stemi', 'myocardial infarction', 'chest pain',
            'hyperlipidemia', 'pain', 'infection', 'fever', 'pneumonia', 'copd',
            'heart failure', 'arrhythmia', 'stroke', 'asthma'
        ]
        
        procedure_keywords = [
            'catheterization', 'surgery', 'biopsy', 'intubation', 'procedure',
            'operation', 'endoscopy', 'colonoscopy', 'angiography', 'stent'
        ]
        
        medication_keywords = [
            'aspirin', 'metformin', 'lisinopril', 'atorvastatin', 'clopidogrel',
            'heparin', 'insulin', 'warfarin', 'levothyroxine', 'amlodipine',
            'omeprazole', 'prednisone', 'albuterol'
        ]
        
        lab_keywords = [
            'troponin', 'ekg', 'blood pressure', 'heart rate', 'glucose',
            'hemoglobin', 'creatinine', 'bun', 'wbc', 'platelets', 'inr',
            'cholesterol', 'ldl', 'hdl', 'triglycerides'
        ]
        
        # Extract problems
        for keyword in problem_keywords:
            if keyword in text_lower:
                offset = text_lower.find(keyword)
                context = self._extract_context(text, offset, len(keyword), context_window=50)
                entities['problems'].append({
                    'text': keyword.title(),
                    'code': 'DEMO-' + keyword.replace(' ', '-').upper(),
                    'code_system': 'ICD-10-CM',
                    'description': keyword.title(),
                    'confidence': 0.85,
                    'context': context
                })
        
        # Extract procedures
        for keyword in procedure_keywords:
            if keyword in text_lower:
                offset = text_lower.find(keyword)
                context = self._extract_context(text, offset, len(keyword), context_window=50)
                entities['procedures'].append({
                    'text': keyword.title(),
                    'code': 'DEMO-' + keyword.replace(' ', '-').upper(),
                    'code_system': 'CPT',
                    'description': keyword.title(),
                    'confidence': 0.80,
                    'context': context
                })
        
        # Extract medications
        for keyword in medication_keywords:
            if keyword in text_lower:
                offset = text_lower.find(keyword)
                context = self._extract_context(text, offset, len(keyword), context_window=50)
                entities['medications'].append({
                    'text': keyword.title(),
                    'code': 'DEMO-' + keyword.replace(' ', '-').upper(),
                    'code_system': 'RxNorm',
                    'description': keyword.title(),
                    'confidence': 0.90,
                    'context': context
                })
        
        # Extract labs
        for keyword in lab_keywords:
            if keyword in text_lower:
                offset = text_lower.find(keyword)
                context = self._extract_context(text, offset, len(keyword), context_window=50)
                entities['labs'].append({
                    'text': keyword.title(),
                    'code': 'DEMO-' + keyword.replace(' ', '-').upper(),
                    'code_system': 'LOINC',
                    'description': keyword.title(),
                    'confidence': 0.75,
                    'context': context
                })
        
        return entities
    
    def normalize_entities(self, entities: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Normalize entities using IMO Precision Normalize API.
        
        Args:
            entities (dict): Extracted entities
            
        Returns:
            dict: Normalized entities with IMO codes
        """
        if not entities:
            return {
                'problems': [],
                'procedures': [],
                'medications': [],
                'labs': []
            }
        
        print(f"Normalizing entities...")
        
        # If no API credentials, use demo normalization
        if not self.client_id or not self.client_secret:
            return self._demo_normalize_entities(entities)
        
        # Get OAuth access token
        access_token = self._get_access_token()
        if not access_token:
            print("Could not obtain access token for normalization, using demo mode")
            return self._demo_normalize_entities(entities)
        
        normalized = {
            'problems': [],
            'procedures': [],
            'medications': [],
            'labs': []
        }
        
        # Normalize each category
        for category, entity_list in entities.items():
            for entity in entity_list:
                try:
                    normalized_entity = self._normalize_single_entity(entity, category, access_token)
                    normalized[category].append(normalized_entity)
                except Exception as e:
                    print(f"Error normalizing entity {entity.get('text')}: {str(e)}")
                    # Add original entity if normalization fails
                    normalized[category].append(entity)
        
        return normalized
    
    def _normalize_single_entity(self, entity: Dict, category: str, access_token: str) -> Dict:
        """
        Normalize a single entity using IMO API.
        Uses enrichment endpoint for problems (with context), regular endpoint for others.
        
        Args:
            entity (dict): Entity to normalize
            category (str): Entity category (problems, procedures, medications, labs)
            access_token (str): OAuth access token
            
        Returns:
            dict: Normalized entity
        """
        import uuid
        
        # Map category to domain
        domain_map = {
            'problems': 'problem',
            'procedures': 'procedure',
            'medications': 'medication',
            'labs': 'lab'
        }
        domain = domain_map.get(category, 'problem')
        
        # Use enrichment endpoint for problems, regular for others
        if category == 'problems':
            url = self.normalize_enrichment_url
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            print(entity.get('context', ''))
            # Build enrichment payload with context
            payload = {
                "organization_id": "IMO",  # Organization ID assigned by IMO
                "client_request_id": str(uuid.uuid4()),
                "preferences": {
                    "threshold": 0.0,
                    "match_field_pref": "input_term",
                    "debug": True,
                    "size": 5
                },
                "requests": [{
                    "record_id": entity.get('entity_id', str(uuid.uuid4())),
                    "domain": domain,
                    "input_term": entity.get('text', ''),
                    #"input_code": entity.get('code', ''),
                    #"input_code_system": entity.get('code_system', ''),
                    "context": {
                        "source_text": entity.get('context', '')
                    }
                }]
            }
            
            print(f"Normalizing problem with enrichment: {entity.get('text', '')}")
            print(f"Enrichment API Request Payload:\n{json.dumps(payload, indent=2)}")
            
        else:
            # Use regular normalize endpoint for other domains
            url = self.normalize_url
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            payload = {
                "organization_id": "IMO",
                "client_request_id": str(uuid.uuid4()),
                "preferences": {
                    "threshold": 0.0,
                    "match_field_pref": "input_term",
                    "debug": True
                },
                "requests": [{
                    "record_id": entity.get('entity_id', str(uuid.uuid4())),
                    "domain": domain,
                    "input_term": entity.get('text', ''),
                    "input_code": entity.get('code', ''),
                    "input_code_system": entity.get('code_system', '')
                }]
            }
            
            print(f"Normalizing {category} entity: {entity.get('text', '')}")
            print(f"Regular Normalize API Request Payload:\n{json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse IMO normalization response (enrichment structure)
                if 'requests' in result and len(result['requests']) > 0:
                    request_data = result['requests'][0]
                    
                    # Check if response exists and has items
                    if 'response' in request_data and 'items' in request_data['response']:
                        items = request_data['response']['items']
                        
                        if len(items) > 0:
                            # Get top match (first item)
                            top_match = items[0]
                            
                            entity['imo_code'] = top_match.get('code', '')
                            entity['imo_lexical_code'] = top_match.get('lexical_code', '')
                            entity['imo_description'] = top_match.get('title', '')
                            entity['imo_lexical_title'] = top_match.get('lexical_title', '')
                            entity['normalized'] = True
                            entity['normalization_confidence'] = top_match.get('score', 0.0)
                            
                            # Check if refinable (from flags)
                            metadata = top_match.get('metadata', {})
                            flags = metadata.get('flags', {})
                            entity['is_refinable'] = flags.get('is_icd10cm_refinable', False)
                            entity['needs_refinement'] = entity['is_refinable']
                            
                            # Store mappings based on category
                            mappings = metadata.get('mappings', {})
                            
                            # ICD-10-CM for problems
                            icd10cm_codes = mappings.get('icd10cm', {}).get('codes', [])
                            if icd10cm_codes:
                                entity['icd10cm_code'] = icd10cm_codes[0].get('code', '')
                                entity['icd10cm_title'] = icd10cm_codes[0].get('title', '')
                                # Add secondary codes if available
                                if len(icd10cm_codes) > 1:
                                    entity['icd10cm_secondary_codes'] = [
                                        {'code': code.get('code', ''), 'title': code.get('title', '')} 
                                        for code in icd10cm_codes[1:]
                                    ]
                            
                            # CPT for procedures
                            cpt_codes = mappings.get('cpt', {}).get('codes', [])
                            if cpt_codes:
                                entity['cpt_code'] = cpt_codes[0].get('code', '')
                                entity['cpt_title'] = cpt_codes[0].get('title', '')
                            
                            # RxNorm for medications
                            rxnorm_codes = mappings.get('rxnorm', {}).get('codes', [])
                            if rxnorm_codes:
                                entity['rxnorm_code'] = rxnorm_codes[0].get('code', '')
                                entity['rxnorm_title'] = rxnorm_codes[0].get('title', '')
                            
                            # LOINC for labs
                            loinc_codes = mappings.get('loinc', {}).get('codes', [])
                            if loinc_codes:
                                entity['loinc_code'] = loinc_codes[0].get('code', '')
                                entity['loinc_title'] = loinc_codes[0].get('title', '')
                            
                            # Store all alternate choices (all remaining items)
                            alternate_choices = []
                            for alt_item in items[1:]:  # Get all alternate choices
                                alt_choice = {
                                    'imo_code': alt_item.get('code', ''),
                                    'lexical_code': alt_item.get('lexical_code', ''),
                                    'title': alt_item.get('title', ''),
                                    'lexical_title': alt_item.get('lexical_title', ''),
                                    'score': alt_item.get('score', 0.0),
                                    'is_refinable': alt_item.get('metadata', {}).get('flags', {}).get('is_icd10cm_refinable', False),
                                    'is_icd10cm_refinable': alt_item.get('metadata', {}).get('flags', {}).get('is_icd10cm_refinable', False)
                                }
                                
                                # Add category-specific codes if available
                                alt_mappings = alt_item.get('metadata', {}).get('mappings', {})
                                
                                # ICD-10-CM
                                alt_icd10cm = alt_mappings.get('icd10cm', {}).get('codes', [])
                                if alt_icd10cm:
                                    alt_choice['icd10cm_code'] = alt_icd10cm[0].get('code', '')
                                    alt_choice['icd10cm_title'] = alt_icd10cm[0].get('title', '')
                                    # Add secondary codes if available
                                    if len(alt_icd10cm) > 1:
                                        alt_choice['icd10cm_secondary_codes'] = [
                                            {'code': code.get('code', ''), 'title': code.get('title', '')} 
                                            for code in alt_icd10cm[1:]
                                        ]
                                
                                # CPT
                                alt_cpt = alt_mappings.get('cpt', {}).get('codes', [])
                                if alt_cpt:
                                    alt_choice['cpt_code'] = alt_cpt[0].get('code', '')
                                    alt_choice['cpt_title'] = alt_cpt[0].get('title', '')
                                
                                # RxNorm
                                alt_rxnorm = alt_mappings.get('rxnorm', {}).get('codes', [])
                                if alt_rxnorm:
                                    alt_choice['rxnorm_code'] = alt_rxnorm[0].get('code', '')
                                    alt_choice['rxnorm_title'] = alt_rxnorm[0].get('title', '')
                                
                                # LOINC
                                alt_loinc = alt_mappings.get('loinc', {}).get('codes', [])
                                if alt_loinc:
                                    alt_choice['loinc_code'] = alt_loinc[0].get('code', '')
                                    alt_choice['loinc_title'] = alt_loinc[0].get('title', '')
                                
                                alternate_choices.append(alt_choice)
                            
                            entity['alternate_choices'] = alternate_choices
                            
                            # Log the result
                            refinable_tag = " [REFINABLE]" if entity['is_refinable'] else ""
                            print(f"  ✓ Normalized to IMO: {entity['imo_code']} - {entity['imo_description']}{refinable_tag}")
                            if alternate_choices:
                                print(f"    Alternate choices: {len(alternate_choices)}")
                        else:
                            print(f"  ⚠ No items found in response for: {entity.get('text', '')}")
                            entity['imo_code'] = ''
                            entity['imo_description'] = entity.get('description', '')
                            entity['normalized'] = False
                            entity['needs_refinement'] = False
                            entity['is_refinable'] = False
                            entity['alternate_choices'] = []
                    else:
                        print(f"  ⚠ No response/items in result for: {entity.get('text', '')}")
                        entity['imo_code'] = ''
                        entity['imo_description'] = entity.get('description', '')
                        entity['normalized'] = False
                        entity['needs_refinement'] = False
                        entity['is_refinable'] = False
                        entity['alternate_choices'] = []
                else:
                    print(f"  ⚠ Invalid response structure")
                    entity['imo_code'] = ''
                    entity['imo_description'] = entity.get('description', '')
                    entity['normalized'] = False
                    entity['needs_refinement'] = False
                    entity['is_refinable'] = False
                    entity['alternate_choices'] = []
                    
            else:
                print(f"  ✗ Normalization API Error: {response.status_code} - {response.text}")
                entity['imo_code'] = ''
                entity['imo_description'] = entity.get('description', '')
                entity['normalized'] = False
                entity['needs_refinement'] = False
                entity['is_refinable'] = False
                entity['alternate_choices'] = []
                
        except Exception as e:
            print(f"  ✗ Error calling normalization API: {str(e)}")
            entity['imo_code'] = ''
            entity['imo_description'] = entity.get('description', '')
            entity['normalized'] = False
            entity['needs_refinement'] = False
            entity['is_refinable'] = False
            entity['alternate_choices'] = []
        
        return entity
    
    def _demo_normalize_entities(self, entities: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Demo normalization (fallback when API not available).
        
        Args:
            entities (dict): Extracted entities
            
        Returns:
            dict: Normalized entities
        """
        normalized = {
            'problems': [],
            'procedures': [],
            'medications': [],
            'labs': []
        }
        
        for category, entity_list in entities.items():
            for entity in entity_list:
                # Add IMO normalization fields
                entity['imo_code'] = f"IMO-{entity.get('code', 'DEMO')}"
                entity['imo_description'] = entity.get('description', entity.get('text', ''))
                entity['normalized'] = True
                entity['needs_refinement'] = self._check_refinement_needed(entity, category)
                
                normalized[category].append(entity)
        
        return normalized
    
    def _check_refinement_needed(self, entity: Dict, category: str) -> bool:
        """
        Check if an entity needs additional refinement.
        
        Args:
            entity (dict): Normalized entity
            category (str): Entity category
            
        Returns:
            bool: True if refinement needed
        """
        # Demo logic: certain entities need refinement
        text = entity.get('text', '').lower()
        
        # Entities that typically need refinement
        refinement_keywords = {
            'problems': ['pain', 'infection', 'disease', 'disorder'],
            'procedures': ['procedure', 'surgery', 'operation'],
            'medications': [],  # Medications usually don't need refinement
            'labs': ['test', 'screen']
        }
        
        keywords = refinement_keywords.get(category, [])
        for keyword in keywords:
            if keyword in text:
                return True
        
        return False
    
    def refine_entities(self, entities_to_refine: List[Dict]) -> List[Dict]:
        """
        Refine entities that need additional specificity.
        
        Args:
            entities_to_refine (list): Entities needing refinement
            
        Returns:
            list: Refined entities with additional specificity
        """
        if not entities_to_refine:
            return []
        
        print(f"Refining {len(entities_to_refine)} entities...")
        
        refined = []
        
        for item in entities_to_refine:
            entity = item.get('entity', {})
            category = item.get('category', '')
            
            # Add refinement suggestions
            refinement_data = {
                'original_entity': entity,
                'category': category,
                'refinement_options': self._get_refinement_options(entity, category),
                'refinement_status': 'pending',
                'refined_at': None
            }
            
            refined.append(refinement_data)
        
        return refined
    
    def _get_refinement_options(self, entity: Dict, category: str) -> List[Dict]:
        """
        Get refinement options for an entity.
        
        Args:
            entity (dict): Entity to refine
            category (str): Entity category
            
        Returns:
            list: Refinement options
        """
        # Demo refinement options
        text = entity.get('text', '').lower()
        
        options = []
        
        if 'pain' in text:
            options = [
                {'code': 'IMO-PAIN-ACUTE', 'description': 'Acute Pain', 'specificity': 'high'},
                {'code': 'IMO-PAIN-CHRONIC', 'description': 'Chronic Pain', 'specificity': 'high'},
                {'code': 'IMO-PAIN-NEUROPATHIC', 'description': 'Neuropathic Pain', 'specificity': 'high'}
            ]
        elif 'infection' in text:
            options = [
                {'code': 'IMO-INFECTION-BACTERIAL', 'description': 'Bacterial Infection', 'specificity': 'high'},
                {'code': 'IMO-INFECTION-VIRAL', 'description': 'Viral Infection', 'specificity': 'high'},
                {'code': 'IMO-INFECTION-FUNGAL', 'description': 'Fungal Infection', 'specificity': 'high'}
            ]
        elif 'procedure' in text or 'surgery' in text:
            options = [
                {'code': 'IMO-PROC-LAPAROSCOPIC', 'description': 'Laparoscopic Procedure', 'specificity': 'high'},
                {'code': 'IMO-PROC-OPEN', 'description': 'Open Procedure', 'specificity': 'high'},
                {'code': 'IMO-PROC-ROBOTIC', 'description': 'Robotic-Assisted Procedure', 'specificity': 'high'}
            ]
        else:
            options = [
                {'code': entity.get('imo_code', 'IMO-REFINED'), 
                 'description': f"Refined {entity.get('text', 'Entity')}", 
                 'specificity': 'medium'}
            ]
        
        return options

    def check_refineable_codes(self, codes: List[Dict]) -> List[Dict]:
        """
        Check which ICD-10-CM codes are refineable using IMO Precision Normalize API.
        
        Args:
            codes (list): List of code dictionaries with 'code' and 'description' keys
            
        Returns:
            list: List of refineable codes with lexical codes
        """
        if not codes:
            return []
        
        print(f"Checking {len(codes)} codes for refinement capability...")
        
        # If no API credentials, return empty (no codes are refineable in demo mode)
        if not self.client_id or not self.client_secret:
            print("No API credentials found, skipping refinement check")
            return []
        
        # Get OAuth access token
        access_token = self._get_access_token()
        if not access_token:
            print("Could not obtain access token for refinement check")
            return []
        
        refineable_codes = []
        
        for code_info in codes:
            try:
                code = code_info.get('code', '')
                description = code_info.get('description', '')
                
                if not code:
                    continue
                
                # Call Precision Normalize API to check refineable flag
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                }
                
                payload = {
                    "organization_id": "IMO",
                    "client_request_id": str(uuid.uuid4()),
                    "preferences": {
                        "threshold": 0.0,
                        "match_field_pref": "input_code",
                        "debug": True,
                        "size": 1
                    },
                    "requests": [{
                        "record_id": str(uuid.uuid4()),
                        "domain": "problem",
                        "input_code": code,
                        "input_code_system": "ICD-10-CM"
                    }]
                }
                
                print(f"Checking code: {code}")
                
                response = requests.post(
                    self.normalize_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                print(f"Normalize API response status: {response.status_code}");
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Parse response to check refineable flag
                    if 'requests' in result and len(result['requests']) > 0:
                        request_data = result['requests'][0]
                        
                        if 'response' in request_data and 'items' in request_data['response']:
                            items = request_data['response']['items']
                            
                            if len(items) > 0:
                                top_match = items[0]
                                metadata = top_match.get('metadata', {})
                                flags = metadata.get('flags', {})
                                is_refinable = flags.get('is_icd10cm_refinable', False)
                                
                                if is_refinable:
                                    lexical_code = top_match.get('lexical_code', '')
                                    refineable_codes.append({
                                        'code': code,
                                        'description': description,
                                        'is_refineable': True,
                                        'lexical_code': lexical_code,
                                        'imo_code': top_match.get('code', ''),
                                        'imo_title': top_match.get('title', '')
                                    })
                                    print(f"  ✓ {code} is refineable (lexical: {lexical_code})")
                                else:
                                    print(f"  ✗ {code} is not refineable")
                else:
                    print(f"  ⚠ API error for {code}: {response.status_code}")
                    
            except Exception as e:
                print(f"  ✗ Error checking code {code_info.get('code', '')}: {str(e)}")
                continue
        
        print(f"\nFound {len(refineable_codes)} refineable codes out of {len(codes)} total")
        return refineable_codes
