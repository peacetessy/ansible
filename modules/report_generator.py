from fpdf import FPDF
import os
from datetime import datetime
from colorama import Fore, init

# Initialize colorama
init(autoreset=True)

def generate_report_pdf(playbook_results):
    """
    Generates a detailed report in PDF format based on the results of Ansible playbooks.
    :param playbook_results: A dictionary containing the results of the playbooks.
    """
    # Create a PDF object
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Add title
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt="Ansible Playbook Report", ln=True, align="C")
    pdf.ln(10)

    # Add date
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(10)

    # Initialize counters for the summary
    total_tasks = 0
    ok_tasks = 0
    failed_tasks = 0
    changed_tasks = 0

    # Add playbook results
    for playbook_name, results in playbook_results.items():
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(200, 10, txt=f"Playbook: {playbook_name}", ln=True)
        pdf.ln(5)

        for host, tasks in results.items():
            pdf.set_font("Arial", style="B", size=12)
            pdf.cell(200, 10, txt=f"  Host: {host}", ln=True)
            pdf.ln(5)

            # Check if tasks are a dictionary (e.g., with sub-keys like interfaces)
            if isinstance(tasks, dict):
                for sub_key, sub_tasks in tasks.items():
                    pdf.set_font("Arial", style="B", size=12)
                    pdf.cell(200, 10, txt=f"    Sub-Key: {sub_key}", ln=True)
                    pdf.ln(5)

                    if isinstance(sub_tasks, list):
                        for task in sub_tasks:
                            if isinstance(task, dict) and 'task_name' in task:
                                total_tasks += 1
                                status = task['status']

                                # Update counters based on status
                                if status == 'ok':
                                    ok_tasks += 1
                                    pdf.set_text_color(0, 128, 0)  # Green
                                elif status == 'failed':
                                    failed_tasks += 1
                                    pdf.set_text_color(255, 0, 0)  # Red
                                elif status == 'changed':
                                    changed_tasks += 1
                                    pdf.set_text_color(0, 0, 255)  # Blue
                                else:
                                    pdf.set_text_color(0, 0, 0)  # Default black

                                # Add task details
                                pdf.set_font("Arial", size=12)
                                pdf.cell(200, 10, txt=f"      Task: {task['task_name']}", ln=True)
                                pdf.cell(200, 10, txt=f"        Status: {status}", ln=True)
                                pdf.cell(200, 10, txt=f"        Message: {task.get('message', 'No additional details.')}", ln=True)
                                pdf.ln(5)

                                # Reset text color to black
                                pdf.set_text_color(0, 0, 0)
                            else:
                                pdf.set_font("Arial", size=12)
                                pdf.cell(200, 10, txt=f"      [ERROR] Unexpected task format: {task}", ln=True)
                                pdf.ln(5)
                    else:
                        pdf.set_font("Arial", size=12)
                        pdf.cell(200, 10, txt=f"      [ERROR] Unexpected sub-task format: {sub_tasks}", ln=True)
                        pdf.ln(5)
            else:
                # Handle tasks directly if not a dictionary
                for task in tasks:
                    if isinstance(task, dict) and 'task_name' in task:
                        total_tasks += 1
                        status = task['status']

                        # Update counters based on status
                        if status == 'ok':
                            ok_tasks += 1
                            pdf.set_text_color(0, 128, 0)  # Green
                        elif status == 'failed':
                            failed_tasks += 1
                            pdf.set_text_color(255, 0, 0)  # Red
                        elif status == 'changed':
                            changed_tasks += 1
                            pdf.set_text_color(0, 0, 255)  # Blue
                        else:
                            pdf.set_text_color(0, 0, 0)  # Default black

                        # Add task details
                        pdf.set_font("Arial", size=12)
                        pdf.cell(200, 10, txt=f"    Task: {task['task_name']}", ln=True)
                        pdf.cell(200, 10, txt=f"      Status: {status}", ln=True)
                        pdf.cell(200, 10, txt=f"      Message: {task.get('message', 'No additional details.')}", ln=True)
                        pdf.ln(5)

                        # Reset text color to black
                        pdf.set_text_color(0, 0, 0)
                    else:
                        pdf.set_font("Arial", size=12)
                        pdf.cell(200, 10, txt=f"    [ERROR] Unexpected task format: {task}", ln=True)
                        pdf.ln(5)

    # Add summary at the end of the report
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(200, 10, txt="Summary", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Total Tasks: {total_tasks}", ln=True)
    pdf.cell(200, 10, txt=f"Tasks OK: {ok_tasks}", ln=True)
    pdf.cell(200, 10, txt=f"Tasks Failed: {failed_tasks}", ln=True)
    pdf.cell(200, 10, txt=f"Tasks Changed: {changed_tasks}", ln=True)

    # Save the PDF to a file
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    pdf.output(report_file)

    print(Fore.GREEN + f"\n[OK] Detailed PDF report generated successfully: {report_file}")
