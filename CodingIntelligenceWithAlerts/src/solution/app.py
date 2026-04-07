from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime
from nlp_processor import NLPProcessor
import config

app = Flask(__name__)
app.secret_key = 'ambient-ai-solution-key'

# Initialize processors

nlp_processor = NLPProcessor()

# Global storage for pipeline state
PIPELINE_STATE = {
    'transcript': None,
    'soap_note': None,
    'entities': None,
    'normalized_entities': None,
    'refinement_needed': []
}

# Health check endpoint
@app.route('/ping', methods=['GET'])
def ping():
    return 'pong', 200

@app.route('/')
def index():
    """
    Render the main application page.
    """
    print(f"\n{'='*80}")
    print("RENDERING INDEX PAGE")
    print(f"{'='*80}")
    print(f"show_normalization_step config value: {config.show_normalization_step}")
    print(f"{'='*80}\n")
    return render_template('index.html', show_normalization_step=config.show_normalization_step)

@app.route('/generate_soap', methods=['POST'])
def generate_soap():
    """
    Generate a SOAP note from medical transcript.
    
    Endpoint: POST /generate_soap
    Input: { "transcript": "medical transcript text..." }
    Output: { "soap_note": {...}, "success": true }
    """
    try:
        data = request.get_json()
        transcript = data.get('transcript', '')
        
        if not transcript or len(transcript.strip()) == 0:
            return jsonify({
                "success": False,
                "error": "Transcript is required"
            }), 400
        
        print(f"\n{'='*80}")
        print("GENERATING SOAP NOTE")
        print(f"{'='*80}\n")
        print(f"Transcript length: {len(transcript)} characters")
        
        # Store transcript in pipeline state
        PIPELINE_STATE['transcript'] = transcript
        
        # Generate SOAP note
        soap_note = soap_generator.generate_soap_note(transcript)
        PIPELINE_STATE['soap_note'] = soap_note
        
        print(f"\nSOAP Note generated successfully")
        print(f"Sections: {', '.join(soap_note.keys())}")
        
        return jsonify({
            "success": True,
            "soap_note": soap_note,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error generating SOAP note: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/extract_entities', methods=['POST'])
def extract_entities():
    """
    Extract entities from SOAP note using IMO Entity Extraction API.
    
    Endpoint: POST /extract_entities
    Input: { "soap_note": {...} }
    Output: { "entities": {...}, "success": true }
    """
    try:
        data = request.get_json()
        attachments = data.get('attachments')
        if not attachments or not isinstance(attachments, list) or len(attachments) == 0:
            return jsonify({
                "success": False,
                "error": "At least one claims attachment is required"
            }), 400

        print(f"\n{'='*80}")
        print("EXTRACTING ENTITIES FROM MULTIPLE CLAIMS ATTACHMENTS")
        print(f"{'='*80}\n")

        entities_by_attachment = []
        for idx, attachment_text in enumerate(attachments):
            print(f"Attachment {idx+1}: {len(attachment_text)} characters")
            entities = nlp_processor.extract_entities(attachment_text)
            entities_by_attachment.append(entities)

        PIPELINE_STATE['entities'] = entities_by_attachment

        print(f"\nEntities extracted for {len(entities_by_attachment)} attachments.")

        return jsonify({
            "success": True,
            "entities": entities_by_attachment,
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        print(f"Error extracting entities: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/validate_billing_codes', methods=['POST'])
def validate_billing_codes():
    """
    Validate ICD-10-CM codes for billing appropriateness using IMO Coding Intelligence API.
    
    Endpoint: POST /validate_billing_codes
    Input: { "codes": [{"code": "A17.0", "code_system": "ICD-10-CM"}, ...] }
    Output: { "validated_codes": [...], "success": true }
    """
    try:
        data = request.get_json()
        codes = data.get('codes', [])
        
        if not codes:
            return jsonify({
                "success": False,
                "error": "Codes are required"
            }), 400
        
        print(f"\n{'='*80}")
        print("VALIDATING BILLING CODES")
        print(f"{'='*80}\n")
        
        # Call IMO Coding Intelligence API
        validated_codes = nlp_processor.validate_billing_codes(codes)
        
        return jsonify({
            "success": True,
            "validated_codes": validated_codes
        }), 200
        
    except Exception as e:
        print(f"Error validating billing codes: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/normalize_entities', methods=['POST'])
def normalize_entities():
    """
    Normalize entities using IMO Precision Normalize API.
    
    Endpoint: POST /normalize_entities
    Input: { "entities": {...} }
    Output: { "normalized_entities": {...}, "refinement_needed": [...], "success": true }
    """
    try:
        data = request.get_json()
        entities = data.get('entities', PIPELINE_STATE.get('entities'))
        
        if not entities:
            return jsonify({
                "success": False,
                "error": "Entities are required"
            }), 400
        
        print(f"\n{'='*80}")
        print("NORMALIZING ENTITIES WITH IMO PRECISION NORMALIZE")
        print(f"{'='*80}\n")
        
        # Normalize entities using IMO API
        normalized_entities = nlp_processor.normalize_entities(entities)
        PIPELINE_STATE['normalized_entities'] = normalized_entities
        
        # Identify entities that need refinement
        refinement_needed = []
        for category, entity_list in normalized_entities.items():
            for entity in entity_list:
                if entity.get('needs_refinement', False):
                    refinement_needed.append({
                        'category': category,
                        'entity': entity
                    })
        
        PIPELINE_STATE['refinement_needed'] = refinement_needed
        
        print(f"\nNormalization complete:")
        print(f"  Total entities normalized: {sum(len(v) for v in normalized_entities.values())}")
        print(f"  Entities needing refinement: {len(refinement_needed)}")
        
        return jsonify({
            "success": True,
            "normalized_entities": normalized_entities,
            "refinement_needed": refinement_needed,
            "refinement_count": len(refinement_needed),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error normalizing entities: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/refine_entities', methods=['POST'])
def refine_entities():
    """
    Trigger refinement workflow for entities that need additional specificity.
    
    Endpoint: POST /refine_entities
    Input: { "entities_to_refine": [...] }
    Output: { "refined_entities": [...], "success": true }
    """
    try:
        data = request.get_json()
        entities_to_refine = data.get('entities_to_refine', PIPELINE_STATE.get('refinement_needed', []))
        
        if not entities_to_refine:
            return jsonify({
                "success": True,
                "message": "No entities need refinement",
                "refined_entities": []
            }), 200
        
        print(f"\n{'='*80}")
        print("REFINING ENTITIES FOR ADDITIONAL SPECIFICITY")
        print(f"{'='*80}\n")
        print(f"Entities to refine: {len(entities_to_refine)}")
        
        # Refine entities
        refined_entities = nlp_processor.refine_entities(entities_to_refine)
        
        print(f"\nRefinement complete:")
        print(f"  Entities refined: {len(refined_entities)}")
        
        return jsonify({
            "success": True,
            "refined_entities": refined_entities,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error refining entities: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/load_sample_transcript', methods=['GET'])
def load_sample_transcript():
    """
    Load a sample medical transcript for testing.
    
    Endpoint: GET /load_sample_transcript
    Output: { "transcript": "...", "success": true }
    """
    try:
        sample_file = os.path.join('sample_data', 'sample_transcript.txt')
        
        if os.path.exists(sample_file):
            with open(sample_file, 'r', encoding='utf-8') as f:
                transcript = f.read()
        else:
            # Fallback sample transcript
            transcript = """Patient is a 58-year-old male presenting with chest pain and shortness of breath. 
He reports the pain started 2 hours ago while at rest, radiating to his left arm. 
Past medical history includes hypertension, type 2 diabetes, and hyperlipidemia. 
Current medications include metformin 1000mg twice daily, lisinopril 10mg daily, and atorvastatin 40mg daily.
Physical exam reveals blood pressure 160/95, heart rate 92, respiratory rate 20.
EKG shows ST elevation in leads V2-V4. Troponin elevated at 2.5.
Assessment: Acute ST-elevation myocardial infarction (STEMI).
Plan: Immediate cardiac catheterization, start aspirin 325mg, clopidogrel 600mg loading dose, 
heparin infusion, admit to CCU, cardiology consult."""
        
        return jsonify({
            "success": True,
            "transcript": transcript
        }), 200
        
    except Exception as e:
        print(f"Error loading sample transcript: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/get_pipeline_state', methods=['GET'])
def get_pipeline_state():
    """
    Get the current state of the pipeline.
    
    Endpoint: GET /get_pipeline_state
    Output: { "state": {...}, "success": true }
    """
    return jsonify({
        "success": True,
        "state": {
            "has_transcript": PIPELINE_STATE['transcript'] is not None,
            "has_soap_note": PIPELINE_STATE['soap_note'] is not None,
            "has_entities": PIPELINE_STATE['entities'] is not None,
            "has_normalized_entities": PIPELINE_STATE['normalized_entities'] is not None,
            "refinement_count": len(PIPELINE_STATE['refinement_needed'])
        }
    }), 200

@app.route('/get_imo_token', methods=['POST'])
def get_imo_token():
    """
    Get IMO OAuth access token for client-side API calls.
    
    Endpoint: POST /get_imo_token
    Output: { "access_token": "...", "success": true }
    """
    try:
        # Get access token from NLP processor
        access_token = nlp_processor._get_access_token()
        
        if not access_token:
            return jsonify({
                "success": False,
                "error": "Failed to obtain access token"
            }), 401
        
        return jsonify({
            "success": True,
            "access_token": access_token
        }), 200
        
    except Exception as e:
        print(f"Error getting IMO token: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/diagnostic_workflow', methods=['POST'])
def diagnostic_workflow():
    """
    Call IMO diagnostic workflow API for a specific lexical code.
    
    Endpoint: POST /diagnostic_workflow
    Input: { "lexical_code": "84356" }
    Output: { "workflow_data": {...}, "success": true }
    """
    try:
        import config
        import requests
        
        data = request.get_json()
        lexical_code = data.get('lexical_code')
        
        if not lexical_code:
            return jsonify({
                "success": False,
                "error": "Lexical code is required"
            }), 400
        
        # Get access token for diagnostic workflow (uses separate credentials)
        access_token = nlp_processor._get_diagnostic_workflow_token()
        
        if not access_token:
            return jsonify({
                "success": False,
                "error": "Failed to obtain diagnostic workflow access token"
            }), 401
        
        # Call diagnostic workflow API
        workflow_url = config.imo_diagnostic_workflow_url
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        # Construct payload per IMO API specification
        payload = {
            'usePreviousVersion': False,
            'sessionId': '00000000-0000-0000-0000-000000000000',
            'imoLexicalCode': str(lexical_code),
            'properties': [],
            'clientApp': 'AmbientAI',
            'clientAppVersion': '1.0',
            'siteId': 'AmbientAI',
            'userId': 'AmbientUser'
        }
        
        print(f"Calling diagnostic workflow API for lexical code: {lexical_code}")
        
        response = requests.post(
            workflow_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            workflow_data = response.json()
            return jsonify({
                "success": True,
                "workflow_data": workflow_data
            }), 200
        else:
            print(f"Diagnostic workflow API error: {response.status_code} - {response.text}")
            return jsonify({
                "success": False,
                "error": f"API returned status {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except Exception as e:
        print(f"Error calling diagnostic workflow API: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/check_refineable', methods=['POST'])
def check_refineable():
    """
    Check which ICD-10-CM codes from CSV are refineable.
    
    Endpoint: POST /check_refineable
    Input: { "codes": [{"code": "E11.9", "description": "..."}, ...] }
    Output: { 
        "success": true,
        "refineable_codes": [
            {
                "code": "E11.9",
                "description": "...",
                "is_refineable": true,
                "lexical_code": "84356"
            }
        ]
    }
    """
    try:
        data = request.get_json()
        codes = data.get('codes', [])
        
        if not codes:
            return jsonify({
                "success": False,
                "error": "Codes are required"
            }), 400
        
        print(f"\n{'='*80}")
        print("CHECKING REFINEABLE CODES")
        print(f"{'='*80}\n")
        print(f"Total codes to check: {len(codes)}")
        
        # Call NLP processor to check refineable codes
        refineable_codes = nlp_processor.check_refineable_codes(codes)
        
        print(f"\nFound {len(refineable_codes)} refineable codes")
        
        return jsonify({
            "success": True,
            "refineable_codes": refineable_codes
        }), 200
        
    except Exception as e:
        print(f"Error checking refineable codes: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/get_alert_rules', methods=['GET'])
def get_alert_rules():
    """
    Load alert rules from a CSV file and return as structured JSON.
    Expected columns (all optional except Code):
      - Code              : the medical code (ICD-10-CM, CPT, etc.)
      - Description       : human-readable label for the code
      - Reason            : the specific reason text shown in the alert for this stop/rule
      - Output Reason     : fallback reason if Reason column is absent
      - Single Soft       : non-empty → this code alone triggers a soft stop
      - Single Hard       : non-empty → this code alone triggers a hard stop
      - Hard              : semicolon-delimited pair key (e.g. "G629/M792") – hard stop when BOTH codes present
      - Soft              : semicolon-delimited pair key (e.g. "G629/E119") – soft stop when BOTH codes present
      - Only if these Codes are not present : comma-delimited codes; hard stop if NONE present alongside this code
    """
    import csv

    rules_file = os.path.join(os.path.dirname(__file__), 'sample_data', 'Rules', 'SIgnifyTest.csv')

    try:
        rules = []
        with open(rules_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('Code', '').strip()
                if not code:
                    continue

                def extract_pairs(field):
                    """Extract only the slash-delimited pair tokens from a field like 'Yes; G629/M792'."""
                    if not field:
                        return ''
                    pairs = [t.strip() for t in field.split(';') if '/' in t]
                    return '; '.join(pairs)

                rule = {
                    'code': code,
                    'description': row.get('Description', '').strip(),
                    'reason': row.get('Reason', '').strip() or row.get('Output Reason', '').strip(),
                    'singleSoft': row.get('Single Soft', '').strip(),
                    'singleHard': row.get('Single Hard', '').strip(),
                    'hard': extract_pairs(row.get('Hard', '')),
                    'soft': extract_pairs(row.get('Soft', '')),
                    'requiredCompanions': [c.strip() for c in row.get('Only if these Codes are not present', '').split(',') if c.strip()],
                }
                rules.append(rule)

        return jsonify({'success': True, 'rules': rules}), 200

    except Exception as e:
        print(f"Error loading alert rules: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/match_rule_bundles', methods=['POST'])
def match_rule_bundles():
    """
    Match uploaded claim codes with rule bundles from Rules CSV files.
    
    Endpoint: POST /match_rule_bundles
    Input: { "codes": [{"code": "27447", "codeSystem": "CPT"}, ...] }
    Output: { 
        "success": true,
        "bundles": [
            {
                "bundleName": "TotalKneeReplacementBundledProcs",
                "fileName": "TotalKneeReplacementBundledProcs_20260220_v1.csv",
                "matchedCodes": ["27447"],
                "allCodes": [
                    {
                        "codeSystem": "CPT",
                        "code": "27447",
                        "description": "Total knee arthroplasty",
                        "required": true,
                        "optional": false
                    },
                    ...
                ]
            }
        ]
    }
    """
    try:
        import csv
        import glob
        
        data = request.get_json()
        uploaded_codes = data.get('codes', [])
        
        if not uploaded_codes:
            return jsonify({
                "success": False,
                "error": "Codes are required"
            }), 400
        
        print(f"\n{'='*80}")
        print("MATCHING RULE BUNDLES")
        print(f"{'='*80}\n")
        print(f"Uploaded codes: {len(uploaded_codes)}")
        for code_obj in uploaded_codes:
            print(f"  - {code_obj.get('codeSystem', 'N/A')}: {code_obj.get('code', 'N/A')}")
        
        def normalize_code_system(code_system):
            """Normalize code system name for matching."""
            # Remove special chars, spaces, hyphens, convert to uppercase
            normalized = ''.join(c for c in code_system if c.isalnum()).upper()
            
            # Handle common patterns
            # CPT®-4, CPT-4, CPT4 → CPT
            if normalized.startswith('CPT'):
                return 'CPT'
            # ICD-10-CM, ICD10CM → ICD10CM
            if normalized.startswith('ICD'):
                return normalized
            # HCPCS Level II → HCPCS
            if normalized.startswith('HCPCS'):
                return 'HCPCS'
            # SNOMED CT → SNOMEDCT
            if 'SNOMED' in normalized:
                return 'SNOMEDCT'
            # LOINC® → LOINC
            if normalized.startswith('LOINC'):
                return 'LOINC'
            
            return normalized
        
        # Create a set of uploaded codes for quick lookup (normalize code system)
        uploaded_code_set = set()
        for code_obj in uploaded_codes:
            code = code_obj.get('code', '').strip()
            code_system = code_obj.get('codeSystem', '').strip()
            code_system_normalized = normalize_code_system(code_system)
            if code:
                uploaded_code_set.add(f"{code_system_normalized}:{code}")
                print(f"  Normalized: {code_system} -> {code_system_normalized}:{code}")
        
        # Find all Rules CSV files
        rules_folder = os.path.join(os.path.dirname(__file__), 'sample_data', 'Rules')
        csv_files = glob.glob(os.path.join(rules_folder, '*.csv'))
        
        print(f"\nFound {len(csv_files)} Rules CSV files")
        
        matching_bundles = []
        
        for csv_file in csv_files:
            print(f"\nProcessing: {os.path.basename(csv_file)}")
            
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    if not rows:
                        print(f"  Empty file, skipping")
                        continue
                    
                    # Get bundle name from first row
                    bundle_name = rows[0].get('Value Set Name', os.path.basename(csv_file).replace('.csv', ''))
                    
                    # Check if any uploaded code matches this bundle
                    matched_codes = []
                    all_bundle_codes = []
                    
                    for row in rows:
                        code_system_raw = row.get('Code system', '').strip()
                        code_system = normalize_code_system(code_system_raw)
                        code = row.get('Code', '').strip()
                        description = row.get('Description', '').strip()
                        required = row.get('Required', '').strip().lower() == 'true'
                        optional = row.get('Optional', '').strip().lower() == 'true'
                        
                        if code:
                            # Add to all bundle codes (keep original code system name for display)
                            all_bundle_codes.append({
                                'codeSystem': code_system_raw,
                                'code': code,
                                'description': description,
                                'required': required,
                                'optional': optional
                            })
                            
                            # Check if this code matches any uploaded code (use normalized key)
                            normalized_key = f"{code_system}:{code}"
                            if normalized_key in uploaded_code_set:
                                matched_codes.append(code)
                                print(f"    MATCH: {code_system_raw} ({code_system}) {code}")
                    
                    # If we found any matches, add this bundle
                    if matched_codes:
                        print(f"  ✓ MATCH! Found {len(matched_codes)} matching code(s)")
                        matching_bundles.append({
                            'bundleName': bundle_name,
                            'fileName': os.path.basename(csv_file),
                            'matchedCodes': matched_codes,
                            'allCodes': all_bundle_codes
                        })
                    else:
                        print(f"  No matches")
                        
            except Exception as e:
                print(f"  Error reading {csv_file}: {str(e)}")
                continue
        
        print(f"\n{'='*80}")
        print(f"Total matching bundles: {len(matching_bundles)}")
        print(f"{'='*80}\n")
        
        return jsonify({
            "success": True,
            "bundles": matching_bundles
        }), 200
        
    except Exception as e:
        print(f"Error matching rule bundles: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    #app.run(debug=True, port=5001)
    app.run(host='0.0.0.0', port=5001) 
