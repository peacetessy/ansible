import sys
import re
import argparse
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os
import traceback
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from modules.config_generator import choose_save_location_cli
"""
Script to generate a modern PDF report from an Ansible log file.
"""

MAX_COLS = 7  # Maximum columns per sub-table (including first column)
MAX_ROWS = 20  # Maximum rows per sub-table (including header)

class AnsibleLogParser:
    def __init__(self, log_file):
        self.log_file = log_file
        self.playbooks = []
        self.hosts = set()
        self.current_playbook = None
        self.current_task = None

    def parse_log(self):
        """Parse the Ansible log file."""
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()

            # Detect a new playbook
            if line.startswith('PLAY [') and not line.startswith('PLAY RECAP'):
                playbook_name = re.search(r'PLAY \[(.*?)\]', line).group(1)
                self.current_playbook = {
                    'name': playbook_name,
                    'tasks': [],
                    'recap': {}
                }
                self.playbooks.append(self.current_playbook)

            # Detect a new task
            elif line.startswith('TASK ['):
                task_name = re.search(r'TASK \[(.*?)\]', line).group(1)
                self.current_task = {
                    'name': task_name,
                    'results': {}
                }
                if self.current_playbook:
                    self.current_playbook['tasks'].append(self.current_task)

            # Detect task results
            elif any(status in line for status in ['ok:', 'changed:', 'failed:', 'skipping:', 'fatal:']):
                if self.current_task:
                    match = re.search(r'(ok|changed|failed|skipping|fatal): \[([^\]]+)\]', line)
                    if match:
                        status, host = match.groups()
                        self.hosts.add(host)
                        self.current_task['results'][host] = status

            # Detect PLAY RECAP
            elif line.startswith('PLAY RECAP'):
                continue

            # Parse recap statistics
            elif ':' in line and any(word in line for word in ['ok=', 'changed=', 'unreachable=', 'failed=']):
                parts = line.split(':')
                if len(parts) == 2:
                    host = parts[0].strip()
                    stats = parts[1].strip()
                    recap_data = {}
                    for stat in stats.split():
                        if '=' in stat:
                            key, value = stat.split('=')
                            recap_data[key] = int(value)
                    if self.current_playbook:
                        self.current_playbook['recap'][host] = recap_data

        return self.playbooks, sorted(list(self.hosts))

def create_summary_table(playbooks, hosts):
    """
    Create the summary table for all hosts.
    OK Tasks = number of tasks with status 'ok' (not 'changed' or 'failed') for this host.
    """
    data = [['Host', 'OK Tasks', 'Changed', 'Failed', 'Status']]
    total_ok = total_changed = total_failed = 0

    for host in hosts:
        host_ok = host_changed = host_failed = 0
        for playbook in playbooks:
            for task in playbook['tasks']:
                status = task['results'].get(host, '')
                if status == 'ok':
                    host_ok += 1
                elif status == 'changed':
                    host_changed += 1
                elif status == 'failed' or status == 'fatal':
                    host_failed += 1
        status = '✓' if host_failed == 0 else '✗'
        data.append([host, str(host_ok), str(host_changed), str(host_failed), status])
        total_ok += host_ok
        total_changed += host_changed
        total_failed += host_failed

    total_status = '✓' if total_failed == 0 else '✗'
    data.append(['Total', str(total_ok), str(total_changed), str(total_failed), total_status])
    return data

def split_table(data, max_cols=MAX_COLS):
    """
    Split a table into sub-tables if it exceeds max_cols columns.
    Returns a list of sub-tables (each is a list of lists).
    """
    header = data[0]
    body = data[1:]
    tables = []

    n = len(header)
    # Always keep the first column (Task or Host)
    for start in range(1, n, max_cols-1):
        end = min(start + max_cols - 1, n)
        sub_header = [header[0]] + header[start:end]
        sub_body = []
        for row in body:
            sub_body.append([row[0]] + row[start:end])
        tables.append([sub_header] + sub_body)
    return tables

def create_playbook_tables(playbooks, hosts):
    """
    Create detailed tables for each playbook.
    If too many columns, split into sub-tables.
    """
    tables_data = []
    for i, playbook in enumerate(playbooks, 1):
        header = ['Task'] + hosts
        table_data = [header]
        for task in playbook['tasks']:
            row = [task['name']]
            for host in hosts:
                status = task['results'].get(host, '-')
                row.append(status)
            table_data.append(row)
        # Split if too many columns
        sub_tables = split_table(table_data, max_cols=MAX_COLS)
        for idx, sub_table in enumerate(sub_tables, 1):
            tables_data.append({
                'title': f"{i}. {playbook['name']}" + (f" (part {idx})" if len(sub_tables) > 1 else ""),
                'data': sub_table
            })
    return tables_data

def generate_pdf_report(log_file, output_file=None):
    """
    Generate a modern styled PDF report from the Ansible log.
    The report will be stored in a 'report' directory (created if needed).
    """
    date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    default_filename = f"ansible_report_{date_str}.pdf"
    prompt_message = f"Please enter the full path and file name to save the report (default: {default_name}): "

    if not output_file:
        output_file = choose_save_location_cli(default_filename, ".pdf", prompt_message)

    # Parse the log
    parser = AnsibleLogParser(log_file)
    playbooks, hosts = parser.parse_log()

    if not playbooks:
        print("Error: No playbook found in the log file.")
        return

    # Register modern fonts if available
    try:
        pdfmetrics.registerFont(TTFont('Roboto', 'Roboto-Regular.ttf'))
        pdfmetrics.registerFont(TTFont('Roboto-Bold', 'Roboto-Bold.ttf'))
        main_font = 'Roboto'
        bold_font = 'Roboto-Bold'
    except:
        main_font = 'Helvetica'
        bold_font = 'Helvetica-Bold'

    # Create the PDF document with modern margins
    doc = SimpleDocTemplate(output_file, pagesize=A4,
                            leftMargin=0.5*inch, rightMargin=0.5*inch,
                            topMargin=0.7*inch, bottomMargin=0.7*inch)

    styles = getSampleStyleSheet()
    story = []

    # Modern custom styles
    styles.add(ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2c3e50'),
        fontName=bold_font,
        underlineProportion=0.08,
        underlineOffset=-2,
        underlineWidth=1.5,
        underline=True
    ))

    styles.add(ParagraphStyle(
        'SubTitle',
        parent=styles['Heading2'],
        fontSize=16,
        leading=20,
        spaceAfter=8,
        spaceBefore=16,
        alignment=TA_LEFT,
        textColor=colors.black,
        fontName=bold_font
    ))

    styles.add(ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading3'],
        fontSize=14,
        leading=18,
        spaceAfter=6,
        spaceBefore=12,
        alignment=TA_LEFT,
        textColor=colors.black,
        fontName=bold_font
    ))

    styles.add(ParagraphStyle(
        'NormalModern',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
        fontName=main_font
    ))

    # Main title and generation date
    story.append(Paragraph("Ansible Execution Report", styles['MainTitle']))
    story.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles['NormalModern']))
    story.append(Spacer(1, 0.4*inch))

    # Summary section
    story.append(Paragraph("Summary", styles['SubTitle']))
    story.append(Spacer(1, 0.2*inch))

    summary_data = create_summary_table(playbooks, hosts)

    # Modern styled summary table with navy header
    summary_table = Table(summary_data, colWidths=[2.5*inch, 1*inch, 1.2*inch, 0.8*inch, 0.8*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), bold_font),
        ('FONTNAME', (0, 1), (-1, -1), main_font),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#95a5a6')),
        ('FONTNAME', (0, -1), (-1, -1), bold_font),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TEXTCOLOR', (-1, 1), (-1, -1), colors.black),  # Default, will override below
    ]))
    # Conditional coloring for status column
    for row_idx, row in enumerate(summary_data[1:], 1):
        if '✓' in row[-1]:
            summary_table.setStyle(TableStyle([
                ('TEXTCOLOR', (-1, row_idx), (-1, row_idx), colors.HexColor('#155724')),
                ('BACKGROUND', (-1, row_idx), (-1, row_idx), colors.HexColor('#d4edda'))
            ]))
        else:
            summary_table.setStyle(TableStyle([
                ('TEXTCOLOR', (-1, row_idx), (-1, row_idx), colors.red)
            ]))

    story.append(summary_table)
    story.append(Spacer(1, 0.5*inch))

    # Details section
    story.append(Paragraph("Detailed Playbooks", styles['SubTitle']))
    story.append(Spacer(1, 0.3*inch))

    playbook_tables = create_playbook_tables(playbooks, hosts)

    for table_info in playbook_tables:
        story.append(Paragraph(table_info['title'], styles['SectionTitle']))
        story.append(Spacer(1, 0.15*inch))

        # Wrap header and task names for long text
        wrapped_data = []
        for i, row in enumerate(table_info['data']):
            if i == 0:
                # Header row: wrap each cell in a white-colored Paragraph, centered and bold
                wrapped_row = [Paragraph(str(cell), ParagraphStyle(
                    'HeaderWhite',
                    parent=styles['NormalModern'],
                    textColor=colors.whitesmoke,
                    alignment=TA_CENTER,
                    fontName=bold_font
                )) for cell in row]
            else:
                wrapped_row = [Paragraph(str(row[0]), styles['NormalModern'])] + row[1:]
            wrapped_data.append(wrapped_row)

        num_cols = len(wrapped_data[0])
        col_widths = [2*inch] + [(6.5*inch-2*inch)/(num_cols-1)]*(num_cols-1) if num_cols > 1 else [6.5*inch]

        table = Table(wrapped_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Center header row
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # First column (task names) left-aligned for data rows
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'), # Data cells centered
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTNAME', (0, 1), (-1, -1), main_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))

        # Highlight 'changed', 'ok', and 'failed' cells
        for row_idx, row in enumerate(wrapped_data[1:], 1):
            for col_idx, cell in enumerate(row[1:], 1):
                cell_value = str(cell)
                if cell_value == 'changed':
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#fff3cd')),
                        ('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#856404')),
                        ('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), bold_font),
                    ]))
                elif cell_value == 'ok':
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#d4edda')),  # light green
                        ('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#155724')),   # dark green
                        ('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), bold_font),
                    ]))
                elif cell_value == 'failed' or cell_value == 'fatal':
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#f8d7da')),  # light red
                        ('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#721c24')),   # dark red
                        ('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), bold_font),
                    ]))

        story.append(table)
        story.append(Spacer(1, 0.4*inch))

    # Build the PDF
    doc.build(story)
    print(f"Report generated: {output_file}")

