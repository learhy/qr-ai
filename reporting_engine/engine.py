import os
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from plm.data_manager import DataManager

class ReportingEngine:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.data_manager = DataManager(os.path.join('project_data', 'qr-ai-data.json'))

    def generate_webpage(self, project_name):
        # Load project data
        project_data = self.data_manager.get_project_status(project_name)

        if not project_data:
            raise ValueError(f"Project '{project_name}' not found.")

        # Prepare data for the template
        template_data = {
            'project_name': project_name,
            'principal_investigator': project_data.get('principal_investigator', 'Not specified'),
            'interviewers': self._get_unique_interviewers(project_data),
            'interviews': project_data.get('interviews', []),
            'learning_goals': project_data.get('learning_goals', {}).get('preprocessed', []),
            'generated_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'meta_analysis': self.data_manager.get_meta_analysis_results(project_name)
        }

        # Render the template
        template = self.env.get_template('report_template.html')
        output = template.render(template_data)

        # Save the output
        output_dir = os.path.join('reports', project_name)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{project_name}_report.html')
        with open(output_file, 'w') as f:
            f.write(output)

        return output_file

    def _get_unique_interviewers(self, project_data):
        interviewers = set()
        for interview in project_data.get('interviews', []):
            interviewers.add(interview.get('interviewer', 'Not specified'))
        return list(interviewers)
