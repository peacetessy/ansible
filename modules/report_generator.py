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

        for switch, tasks in results.items():
            # Ignore unexpected keys that are not valid switches
            if not isinstance(tasks, list):
                pdf.set_font("Arial", size=12)
                pdf.multi_cell(200, 10, txt=f"[ERROR] Unexpected task format : {switch}")
                pdf.ln(5)
                continue

            pdf.set_font("Arial", style="B", size=12)
            pdf.cell(200, 10, txt=f"  Switch: {switch}", ln=True)
            pdf.ln(5)

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
                    pdf.multi_cell(200, 10, txt=f"      Message: {task.get('message', 'No additional details.')}")
                    pdf.ln(5)

                    # Reset text color to black
                    pdf.set_text_color(0, 0, 0)
                else:
                    pdf.set_font("Arial", size=12)
                    pdf.multi_cell(200, 10, txt=f"    [ERROR] Unexpected task format : {task}")
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
