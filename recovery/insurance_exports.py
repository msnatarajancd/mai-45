"""Saved-snapshot-only exports. No model, insurer or network integration."""
import csv
import io
import json
import re
import zipfile
from pathlib import Path
import reportlab
from html import escape
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, Table, TableStyle
from .insurance_models import InsuranceProfile, ItemPreparation

PACKAGE_LABEL = 'USER-REPORTED INSURANCE PREPARATION \u2014 NOT A SUBMITTED CLAIM'
LIMITATIONS = ('Fictional educational prototype. These are user-confirmed reports, not independent verification. '
    'Coverage, eligibility, damage values and insurer deadlines have not been determined. '
    'ReadyRelief has not contacted an insurer or submitted a claim. '
    'Collect information only when safe; do not enter unsafe premises or handle hazards for photographs. '
    'Original attachments may contain EXIF/GPS metadata. No production-grade document security is provided.')


def known(value):
    if value is None or value == '':
        return 'Unknown / not supplied'
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    return str(value)


def missing_information(snapshot):
    missing = [('Insurance Details', name.replace('_', ' ').title())
               for name, value in snapshot.workspace.profile.model_dump().items() if value is None or value == '']
    details = {item.damage_id: item for item in snapshot.workspace.items}
    for item in snapshot.records.damage_records:
        detail = details.get(item.damage_id, ItemPreparation(damage_id=item.damage_id))
        missing.extend(('Damage Inventory', item.item_description + ': ' + name.replace('_', ' '))
            for name, value in detail.model_dump().items() if name != 'damage_id' and (value is None or value == ''))
    if not snapshot.records.damage_records:
        missing.append(('Damage Inventory', 'No confirmed damaged items recorded'))
    if not snapshot.attachments:
        missing.append(('Evidence & Documents', 'No files saved; existing photographs can be added when safe'))
    if not snapshot.workspace.communications:
        missing.append(('Evidence & Documents', 'No insurer communications reported; contact has not been inferred'))
    return missing


def inventory_csv(snapshot):
    output = io.StringIO(newline='')
    fields = ['package_label', 'damage_id', 'item_description', 'damage_description', 'incident_date', 'notes']
    extra = [name for name in ItemPreparation.model_fields if name not in {'damage_id', 'notes'}] + ['preparation_notes']
    writer = csv.writer(output)
    writer.writerow(fields + extra)
    details = {item.damage_id: item for item in snapshot.workspace.items}
    def safe(value):
        text = known(value)
        # Excel may interpret leading whitespace/control characters before a formula.
        return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')) else text
    for item in snapshot.records.damage_records:
        detail = details.get(item.damage_id, ItemPreparation(damage_id=item.damage_id))
        row = [PACKAGE_LABEL, item.damage_id, item.item_description, item.damage_description, item.incident_date, item.notes]
        row += [getattr(detail, name) if name != 'preparation_notes' else detail.notes for name in extra]
        writer.writerow([safe(value) for value in row])
    return output.getvalue().encode('utf-8-sig')


def preparation_pdf(snapshot):
    """Household-facing presentation; saved records and ZIP references remain unchanged."""
    output = io.BytesIO()
    font_dir = Path(reportlab.__file__).parent / 'fonts'
    for name, filename in (('Preparation', 'Vera.ttf'), ('Preparation-Bold', 'VeraBd.ttf')):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
    pdfmetrics.registerFontFamily('Preparation', normal='Preparation', bold='Preparation-Bold',
                                  italic='Preparation', boldItalic='Preparation-Bold')
    supported = set(pdfmetrics.getFont('Preparation').face.charToGlyph)
    unsupported = set()
    styles = getSampleStyleSheet()
    for name in ('BodyText', 'Title', 'Heading1', 'Heading2'):
        styles[name].fontName = 'Preparation-Bold' if name != 'BodyText' else 'Preparation'
        styles[name].textColor = colors.HexColor('#172B4D')
    styles['BodyText'].fontSize = 9
    styles['BodyText'].leading = 13
    styles['BodyText'].spaceAfter = 5
    styles['Title'].fontSize = 23
    styles['Title'].leading = 28
    styles['Heading1'].fontSize = 14
    styles['Heading1'].leading = 18
    styles['Heading1'].spaceBefore = 14
    styles['Heading1'].spaceAfter = 8
    styles['Heading2'].fontSize = 10
    styles['Heading2'].leading = 14
    styles.add(ParagraphStyle('Small', parent=styles['BodyText'], fontSize=7.5, leading=11))
    story = []

    def para(value, style='BodyText'):
        text = str(value)
        chars = []
        for character in text:
            if character in '\n\t' or ord(character) in supported:
                chars.append(character)
            else:
                unsupported.add(f'U+{ord(character):04X}')
                chars.append(f'[U+{ord(character):04X}]')
        return Paragraph(escape(''.join(chars)).replace('\n', '<br/>'), styles[style])

    def section(title):
        story.append(para(title, 'Heading1'))

    def lines(values):
        return [para(label + ': ' + known(value)) for label, value in values if value is not None and value != '']

    def cost(detail):
        if detail.estimated_cost is None:
            return 'Not estimated'
        return f'{detail.estimated_cost:,.2f}' + (' ' + detail.currency if detail.currency else ' (currency not supplied)')

    story += [para('Insurance Preparation Package', 'Title'), para(PACKAGE_LABEL, 'Heading2'),
        para('This package organizes user-reported information. It is not a submitted claim. '
             'Contact your insurer through an independently verified official channel to confirm '
             'required forms, evidence and submission procedures.'), para(LIMITATIONS, 'Small')]
    section('Incident overview')
    profile = snapshot.workspace.profile
    story += lines([('Reported disaster', snapshot.case.intake.disaster_type),
                    ('Reported housing condition', snapshot.case.intake.housing_condition),
                    ('Incident date', profile.incident_date), ('Property description', profile.property_description)])
    story.append(para('Utility restoration does not establish household safety.', 'Small'))
    section('Insurance information')
    insurance = lines([('Insurer', profile.insurer_name), ('Insurance type', profile.insurance_type),
        ('Policy reference', profile.policy_reference), ('Claim reference', profile.claim_reference),
        ('Insurer contacted (user report)', profile.insurer_contacted), ('Notes', profile.notes)])
    story += insurance or [para('Insurance details have not been supplied. They may be added later.')]
    section('Itemized damage inventory')
    details = {item.damage_id: item for item in snapshot.workspace.items}
    items = {item.damage_id: item.item_description for item in snapshot.records.damage_records}
    if not items:
        story.append(para('No confirmed damaged items recorded.'))
    else:
        rows = [[para(x, 'Small') for x in ('Damaged item', 'Reported description', 'User-estimated cost', 'Saved files')]]
        for item in snapshot.records.damage_records:
            detail = details.get(item.damage_id, ItemPreparation(damage_id=item.damage_id))
            count = sum(p.metadata.damage_id == item.damage_id for p in snapshot.attachments)
            rows.append([para(item.item_description), para(item.damage_description), para(cost(detail)), para(count)])
        table = Table(rows, colWidths=[100, 228, 109, 62], repeatRows=1, splitByRow=1, splitInRow=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E7EEF5')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOX', (0,0), (-1,-1), .5, colors.HexColor('#BCC8D5')),
            ('LINEBELOW', (0,0), (-1,0), .7, colors.HexColor('#8295AC')),
            ('INNERGRID', (0,1), (-1,-1), .3, colors.HexColor('#D8E0E8')),
            ('LEFTPADDING', (0,0), (-1,-1), 8), ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
        story += [table, Spacer(1, 8)]
    for item in snapshot.records.damage_records:
        detail = details.get(item.damage_id, ItemPreparation(damage_id=item.damage_id))
        block = [para(item.item_description + ' - reported item details', 'Heading2')]
        block += lines([('User-estimated cost', cost(detail)), ('Incident date', item.incident_date),
            ('Category', detail.category), ('Location', detail.location), ('Quantity', detail.quantity),
            ('Brand', detail.brand), ('Model', detail.model), ('Serial reference', detail.serial_reference),
            ('Purchase date', detail.purchase_date), ('Purchase price',
                (str(detail.purchase_price) + (' ' + detail.currency if detail.currency else ' (currency not supplied)'))
                if detail.purchase_price is not None else None)])
        # Keep the heading, cost and short facts together. KeepTogether releases an
        # over-page block for splitting; long narrative fields remain splittable.
        narratives = lines([('Reported damage', item.damage_description), ('Damage notes', item.notes),
                            ('Additional damage', detail.additional_damage), ('Preparation notes', detail.notes)])
        full = block + narratives
        height = sum(flow.wrap(499, 700)[1] + flow.getSpaceAfter() + flow.getSpaceBefore() for flow in full)
        if height < 650:
            story.append(KeepTogether(full))
        else:
            story.append(KeepTogether(block))
            story += narratives
        story.append(Spacer(1, 8))
    section('Supporting evidence')
    story.append(para('Saved files below are included in the companion evidence ZIP. '
                      'Reported documents without a saved file are not attached.', 'Small'))
    attachments = {p.metadata.attachment_id: p.metadata for p in snapshot.attachments}
    for index, evidence in enumerate(snapshot.workspace.evidence, 1):
        attachment = attachments.get(evidence.attachment_id)
        item_name = items.get(evidence.damage_id, 'General incident evidence')
        block = [para(f'{index}. {item_name} - {evidence.evidence_type.value}', 'Heading2')]
        if attachment:
            block += [para('File: ' + attachment.original_name),
                      para('Included in companion ZIP: attachments/' + attachment.safe_filename, 'Small')]
        else:
            block.append(para(evidence.status.value + '. No file included in companion ZIP.'))
        descriptions = list(dict.fromkeys(value for value in
            (evidence.description, attachment.description if attachment else '') if value))
        block += [para(value) for value in descriptions]
        block += lines([('User-reported evidence date', evidence.relevant_date)])
        story += [KeepTogether(block), Spacer(1, 6)]
    if not snapshot.workspace.evidence:
        story.append(para('No supporting evidence has been reported or saved.'))
    section('Insurer communication history')
    if not snapshot.workspace.communications:
        story.append(para('No communications reported. Insurer contact is not inferred.'))
    for entry in snapshot.workspace.communications:
        block = lines([('Contact date', entry.contact_date), ('Method', entry.method),
            ('Representative', entry.representative), ('Reference', entry.reference)])
        story += [KeepTogether(block), para('User-reported summary: ' + entry.summary)]
        story += lines([('Next follow-up', entry.next_follow_up)])
    section('Questions and next steps')
    for question in ('Confirm which forms and evidence your insurer requires and how to submit them.',
                     'Ask which procedures and deadlines apply to your policy; none are determined here.',
                     'Ask how your policy addresses the reported circumstances; coverage is not determined here.',
                     'Clarify what to record before repairs or replacing items, without entering unsafe premises.'):
        story.append(para(question))
    section('Optional information to add')
    story.append(para('Add only information useful to your discussion. These are optional preparation prompts, not requirements.'))
    if any(getattr(profile, name) is None for name in ('insurance_type', 'policy_reference', 'incident_date', 'property_description')):
        story.append(para('Policy and incident: check your policy documents and add missing policy or incident details when available.'))
    if any(details.get(i, ItemPreparation(damage_id=i)).estimated_cost is None for i in items):
        story.append(para('Item values: add user estimates, currency and purchase details when known; estimates are not verified losses.'))
    story.append(para('Supporting records: add existing photographs, receipts or estimates if available and safe to obtain. '
                      'Keep notes of insurer discussions and agreed follow-up steps.'))
    if unsupported:
        story.append(para('Text rendering note: characters unavailable in the embedded font are shown as code-point references ('
                          + ', '.join(sorted(unsupported)) + '). Original saved text is unchanged.', 'Small'))

    def footer(canvas, document):
        canvas.setStrokeColor(colors.HexColor('#BCC8D5'))
        canvas.line(48, 36, 547, 36)
        canvas.setFont('Preparation', 7)
        canvas.drawString(48, 24, 'ReadyRelief | User-reported preparation - NOT A SUBMITTED CLAIM')
        canvas.drawRightString(547, 24, str(document.page))
    SimpleDocTemplate(output, rightMargin=48, leftMargin=48, topMargin=40, bottomMargin=50,
                      title='Insurance Preparation Package - NOT A SUBMITTED CLAIM',
                      author='ReadyRelief', invariant=1).build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


def build_preparation_package(repo, case_id):
    """The only public package boundary: reload one consistent, verified saved snapshot."""
    snapshot = repo.get_insurance_snapshot(case_id)
    pdf, inventory = preparation_pdf(snapshot), inventory_csv(snapshot)
    manifest = dict(label=PACKAGE_LABEL, limitations=LIMITATIONS, case_id=str(case_id),
        records_version=snapshot.records.version, workspace_version=snapshot.workspace.version,
        generated_at=datetime.now(timezone.utc).isoformat(), attachments=[dict(
            attachment_id=str(p.metadata.attachment_id), damage_id=str(p.metadata.damage_id) if p.metadata.damage_id else None,
            evidence_category=p.metadata.evidence_type.value, safe_filename='attachments/'+p.metadata.safe_filename,
            original_name=p.metadata.original_name, sha256=p.metadata.sha256, byte_count=p.metadata.byte_count)
            for p in snapshot.attachments], evidence=[e.model_dump(mode='json') for e in snapshot.workspace.evidence])
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zip:
        zip.writestr('insurance-preparation.pdf', pdf)
        zip.writestr('damage-inventory.csv', inventory)
        zip.writestr('evidence-manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False))
        for photo in snapshot.attachments:
            zip.writestr('attachments/'+photo.metadata.safe_filename, photo.content)
    return pdf, inventory, archive.getvalue()
