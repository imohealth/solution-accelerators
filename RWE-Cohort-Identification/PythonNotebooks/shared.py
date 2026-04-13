import requests
import json
import xlsxwriter
from typing import List
import os

# Configuration variables
valid_entity_types = ["problem", "drug", "test", "treatment", "imo_procedure", "procedure", "medication", "lab", "clinical_observation", "social_factor", "age group", "gender"]

class WorkbookModel:
    def __init__(self, file_name, run_time, text, begin, end, assertion, context, section_header, complete_entity,
                 semantic_tag, semantic_category, lexical_code, lexical_title, default_lexical_code, default_lexical_title, confidence,
                 icd10cm, snomedInternational, cpt, loinc, rxnorm, 
                 hospitalGuid=None, encounterGuid=None, patientGuid=None):
        self.file_name = file_name
        self.run_time = run_time
        self.text = text
        self.begin = begin
        self.end = end
        self.assertion = assertion
        self.context = context
        self.section_header = section_header
        self.complete_entity = complete_entity
        self.semantic_tag = semantic_tag
        self.semantic_category = semantic_category
        self.lexical_code = lexical_code
        self.lexical_title = lexical_title
        self.default_lexical_code = default_lexical_code
        self.default_lexical_title = default_lexical_title
        self.confidence = confidence
        self.icd10cm = icd10cm
        self.snomedInternational = snomedInternational
        self.cpt = cpt
        self.loinc = loinc
        self.rxnorm = rxnorm
        self.hospitalGuid = hospitalGuid
        self.encounterGuid = encounterGuid
        self.patientGuid = patientGuid

def get_sentence(entity_begin, entity_end, sentences):
    for sentence in sentences:
        if sentence.get('begin') <= entity_begin and sentence.get('end') >= entity_end:
            return sentence.get('text')
        
    return "ERROR: No sentence found."

def get_complete_entity(entity_text, entity_begin, linked_entities):
    if linked_entities:
        entity_map = {}
        entity_map[entity_begin] = entity_text
        for linked_entity in linked_entities:
            linked_entity_begin = int(linked_entity.get('id').split('_')[0])
            linked_entity_text = linked_entity.get('text')
            entity_map[linked_entity_begin] = linked_entity_text
        complete_entity = ' '.join([entity_map[key] for key in sorted(entity_map.keys())])
        return complete_entity
    return entity_text

def get_imo_lexical(codemaps):
    lexical_code = codemaps.get('imo', {}).get('lexical_code')
    lexical_title = codemaps.get('imo', {}).get('lexical_title')
    default_lexical_code = codemaps.get('imo', {}).get('default_lexical_code')
    default_lexical_title = codemaps.get('imo', {}).get('default_lexical_title')
    confidence = codemaps.get('imo', {}).get('confidence')
    return lexical_code, lexical_title, default_lexical_title, default_lexical_code, confidence

def get_standard_code_maps(codemaps, codesystem):
    codes_str = ""
    if codemaps is None:
        return codes_str
    code_system_codes = codemaps.get(codesystem, {}).get("codes", [])
    for code in code_system_codes:
        #codes_str += "- " +code.get("map_type") + " - " + code.get("code") + " (" + code.get("title") + ")\r\n"
        codes_str = code.get("code")
        break
    return codes_str

def get_rxnorm_code_maps(codemaps):
    # TODO: Handle titles
    codes_str = ""
    if codemaps is None:
        return codes_str
    code_system_codes = codemaps.get('rxnorm', {}).get("codes", [])
    for code in code_system_codes:
        #codes_str += "- " + code.get("rxnorm_code") + "\r\n"
        codes_str = code.get("rxnorm_code")
        break
    return codes_str


def get_entities(api_response, file_name, run_time = "", hospitalGuid=None, encounterGuid=None, patientGuid=None) -> List[WorkbookModel]:
    entities: List[WorkbookModel] = []
    for entity in api_response.get('entities'):
        if entity.get('semantic') in valid_entity_types:
            codemaps = entity.get('codemaps', {})
            lexical_code, lexical_title, default_lexical_title, default_lexical_code, confidence = get_imo_lexical(codemaps)
            output_entity = WorkbookModel(
                file_name = file_name,
                run_time = run_time,
                text = entity.get('text'), 
                begin = entity.get('begin'), 
                end = entity.get('end'),
                assertion = entity.get('assertion'),
                context = get_sentence(entity.get('begin'), entity.get('end'), api_response.get('sentences')) if api_response.get('sentences') else entity.get('explanation'),
                section_header = entity.get('section'),
                complete_entity = get_complete_entity(entity.get('text'), entity.get('begin'), entity.get('linked_entities')),
                semantic_tag = entity.get('semantic'),
                semantic_category = entity.get('semantic_category'),
                lexical_code = lexical_code,
                lexical_title = lexical_title,
                default_lexical_code = default_lexical_code,
                default_lexical_title = default_lexical_title,
                confidence = confidence,
                icd10cm = get_standard_code_maps(codemaps, "icd10cm").strip(),
                snomedInternational = get_standard_code_maps(codemaps, "snomedInternational").strip(),
                cpt = get_standard_code_maps(codemaps, "cpt").strip(),
                loinc = get_standard_code_maps(codemaps, "loinc").strip(),
                rxnorm = get_rxnorm_code_maps(codemaps).strip(),
                hospitalGuid = hospitalGuid,
                encounterGuid = encounterGuid,
                patientGuid = patientGuid
            )
            entities.append(output_entity)
    return entities

def create_workbook(output_workbook_name, api_response_payloads):
    # Ensure output directory exists
    os.makedirs('./Output', exist_ok=True)
    workbook = xlsxwriter.Workbook(f'./Output/{output_workbook_name}')
    left_top_format = workbook.add_format({
        'align': 'left',
        'valign': 'top',
        'text_wrap': True
    })
    wrap = workbook.add_format({
        'text_wrap': True
    })
    bold = workbook.add_format({'bold': True})
    worksheet = workbook.add_worksheet('Results')
    notes_worksheet = workbook.add_worksheet('Notes')
    
    # Add GUID columns at the beginning
    worksheet.write('A1', 'Hospital GUID', bold)
    worksheet.write('B1', 'Encounter GUID', bold)
    worksheet.write('C1', 'Patient GUID', bold)
    worksheet.write('D1', 'Filename', bold)
    worksheet.write('E1', 'Processing Time (s)', bold)
    worksheet.set_column('F:F', 55)
    worksheet.write('F1', 'Context', bold)
    worksheet.set_column('G:G', 20)
    worksheet.write('G1', 'Section', bold)
    worksheet.set_column('H:I', 35)
    worksheet.write('H1', 'Entity', bold)
    worksheet.write('I1', 'Complete Entity', bold)
    worksheet.set_column('J:J', 15)
    worksheet.write('J1', 'Semantic Tag', bold)
    worksheet.set_column('K:K', 18)
    worksheet.write('K1', 'Semantic Category', bold)
    worksheet.set_column('L:L', 12)
    worksheet.write('L1', 'Status', bold)
    worksheet.set_column('M:M', 18)
    worksheet.write('M1', 'Lexical Code', bold)
    worksheet.set_column('N:N', 45)
    worksheet.write('N1', 'Lexical Title', bold)
    worksheet.set_column('O:O', 18)
    worksheet.write('O1', 'Default Lexical Code', bold)
    worksheet.set_column('P:P', 45)
    worksheet.write('P1', 'Default Lexical Title', bold)
    worksheet.set_column('Q:Q', 11)
    worksheet.write('Q1', 'Confidence', bold)
    worksheet.set_column('R:V', 75)
    worksheet.write('R1', 'ICD10CM', bold)
    worksheet.write('S1', 'SNOMED International', bold)
    worksheet.write('T1', 'CPT', bold)
    worksheet.write('U1', 'LOINC', bold)
    worksheet.write('V1', 'RXNORM', bold)
    
    all_entities: list[WorkbookModel] = []

    notes_tab_row = 1
    for file_name, response_obj in api_response_payloads.items():
        # Extract GUIDs from response object (may be None for file-based processing)
        hospitalGuid = response_obj.get('hospitalGuid')
        encounterGuid = response_obj.get('encounterGuid')
        patientGuid = response_obj.get('patientGuid')
        
        entities = get_entities(
            response_obj.get('payload'), 
            file_name, 
            response_obj.get('run_time', ''),
            hospitalGuid=hospitalGuid,
            encounterGuid=encounterGuid,
            patientGuid=patientGuid
        )
        notes_worksheet.write('A' + str(notes_tab_row), file_name)
        notes_worksheet.write('B' + str(notes_tab_row), response_obj.get('payload').get('content'))
        all_entities.extend(entities)
        notes_tab_row += 1

    row = 2
    for entity in all_entities:
        worksheet.write('A' + str(row), entity.hospitalGuid if entity.hospitalGuid else '')
        worksheet.write('B' + str(row), entity.encounterGuid if entity.encounterGuid else '')
        worksheet.write('C' + str(row), entity.patientGuid if entity.patientGuid else '')
        worksheet.write('D' + str(row), entity.file_name)
        worksheet.write('E' + str(row), entity.run_time)
        worksheet.write('F' + str(row), entity.context, wrap)
        worksheet.write('G' + str(row), entity.section_header)
        worksheet.write('H' + str(row), entity.text)
        worksheet.write('I' + str(row), entity.complete_entity)
        worksheet.write('J' + str(row), entity.semantic_tag)
        worksheet.write('K' + str(row), entity.semantic_category)
        worksheet.write('L' + str(row), entity.assertion)
        worksheet.write('M' + str(row), entity.lexical_code)
        worksheet.write('N' + str(row), entity.lexical_title)
        worksheet.write('O' + str(row), entity.default_lexical_code)
        worksheet.write('P' + str(row), entity.default_lexical_title)
        worksheet.write('Q' + str(row), entity.confidence)
        worksheet.write('R' + str(row), entity.icd10cm, left_top_format)
        worksheet.write('S' + str(row), entity.snomedInternational, left_top_format)
        worksheet.write('T' + str(row), entity.cpt, left_top_format)
        worksheet.write('U' + str(row), entity.loinc, left_top_format)
        worksheet.write('V' + str(row), entity.rxnorm, left_top_format)
        
        # Handle when we have multi-line strings for code maps...
        row_new_lines = max(entity.icd10cm.count('\r\n'), entity.snomedInternational.count('\r\n'), entity.cpt.count('\r\n'), entity.loinc.count('\r\n'), entity.rxnorm.count('\r\n'), 1)
        row_height = row_new_lines * 16
        # Row is used with letters for writes (e.g. A2, B2), but when used with set_row, it's 0-indexed
        if row_new_lines > 1:
            # Row is used with letters for writes (e.g. A2, B2), but when used with set_row, it's 0-indexed so we add 1
            worksheet.set_row(row + 1, row_height)

        row += 1

    workbook.close()