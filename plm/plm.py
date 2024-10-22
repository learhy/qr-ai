import os
import configparser
from .data_manager import DataManager
from ppe.ppe import PreprocessorEngine
import shutil
from pydub import AudioSegment
import glob
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown

class ProjectLifecycleManager:
    def __init__(self, file_path):
        self.data_manager = DataManager(file_path)
        self.global_config = configparser.ConfigParser()
        global_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'qr-ai.conf')
        self.global_config.read(global_config_path)
        self.ppe = PreprocessorEngine()
        
        # Ensure the project_data directory exists
        project_data_dir = os.path.dirname(file_path)
        os.makedirs(project_data_dir, exist_ok=True)

    def _get_project_config(self, project_dir):
        config = configparser.ConfigParser()
        config_path = os.path.join(project_dir, 'project_data', os.path.basename(project_dir), 'project.conf')
        config.read(config_path)
        return config

    def _save_project_config(self, project_dir, config):
        config_path = os.path.join(project_dir, 'project_data', os.path.basename(project_dir), 'project.conf')
        with open(config_path, 'w') as configfile:
            config.write(configfile)

    def get_project(self, directory):
        default_project_name = os.path.basename(directory)
        projects = self.data_manager.list_projects()
        
        if default_project_name in projects:
            print(f"Project '{default_project_name}' found.")
            return default_project_name
        
        print(f"No project found in '{directory}'.")
        return None

    def create_project(self, directory):
        default_project_name = os.path.basename(directory)
        
        project_name = input(f"Enter project name (default: '{default_project_name}'): ").strip()
        if not project_name:
            project_name = default_project_name
        
        default_pi = self.global_config.get('Project', 'default_principal_investigator', fallback='')
        principal_investigator = input(f"Creating new project '{project_name}'. Enter principal investigator name (default: '{default_pi}'): ").strip()
        if not principal_investigator:
            principal_investigator = default_pi
        
        project_data_dir = os.path.join(directory, 'project_data', project_name)
        os.makedirs(project_data_dir, exist_ok=True)
        
        if self.data_manager.create_project(project_name, principal_investigator):
            # Create and save project-specific config
            project_config = configparser.ConfigParser()
            project_config['Project'] = {
                'name': project_name,
                'principal_investigator': principal_investigator
            }
            self._save_project_config(directory, project_config)
            print(f"Project '{project_name}' created successfully.")
            return project_name
        else:
            print(f"Failed to create project '{project_name}'.")
            return None

    def get_project_pi(self, project_name):
        project_config = self._get_project_config(os.path.join(os.getcwd(), project_name))
        return project_config.get('Project', 'principal_investigator', fallback=self.global_config.get('Project', 'default_principal_investigator'))

    def set_learning_goal(self, project_name, goal):
        goal_lines = goal.split('\n')
        if self.data_manager.set_learning_goal(project_name, goal_lines):
            print(f"Learning goal set for project '{project_name}'.")
            print("Note: Markdown formatting is supported for learning goals.")
        else:
            print(f"Project '{project_name}' does not exist.")

    def set_interview(self, project_name, interviewee_name, interviewer_name, interview_date):
        interview_name = f"Interview with {interviewee_name}"
        if self.data_manager.set_interview(project_name, interview_name, interviewee_name, interviewer_name, interview_date):
            print(f"Interview '{interview_name}' set for project '{project_name}'.")
            return interview_name
        else:
            print(f"Project '{project_name}' does not exist.")
            return None

    def import_files(self, project_name):
        project_dir = os.getcwd()
        project_data_dir = os.path.join(project_dir, "project_data", project_name)
        audio_dir = os.path.join(project_data_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        files = [f for f in os.listdir(project_dir) if os.path.isfile(os.path.join(project_dir, f)) and self._is_valid_file(f)]
        if not files:
            print(f"No valid files found in the project directory: {project_dir}")
            return

        imported_files = self.data_manager.get_imported_files(project_name)

        print("Valid files found in the project directory:")
        for i, file in enumerate(files, 1):
            status = "Already imported" if self._is_file_imported(file, imported_files) else "New"
            print(f"{i}. {file} ({status})")

        while True:
            choice = input("Enter the numbers of files to import (comma-separated), 'all' for all files, or press Enter to exit: ").strip().lower()
            
            if choice == '':
                print("Import process cancelled.")
                return
            elif choice == 'all':
                files_to_import = [f for f in files if not self._is_file_imported(f, imported_files)]
                break
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in choice.split(',')]
                    files_to_import = [files[i] for i in indices if 0 <= i < len(files) and not self._is_file_imported(files[i], imported_files)]
                    if not files_to_import:
                        print("No valid new files selected. Please try again.")
                    else:
                        break
                except ValueError:
                    print("Invalid input. Please enter numbers, 'all', or press Enter to exit.")

        for file in files_to_import:
            file_path = os.path.join(project_dir, file)
            file_type = self._get_file_type(file)

            if file_type == 'audio':
                original_filename, wav_filename = self._process_audio_file(file_path, audio_dir)
                self.data_manager.update_audio_files(project_name, original_filename, wav_filename)
            elif file_type == 'vtt':
                self._process_vtt_file(project_name, file_path, file)
                # Associate the most recently added audio file with this VTT file
                self.data_manager.associate_latest_audio_with_vtt(project_name, file)
            else:
                print(f"Skipping file: {file} (unsupported type)")

        print("Import process completed.")

    def _is_file_imported(self, filename, imported_files):
        name, ext = os.path.splitext(filename)
        return any(imported.startswith(name) for imported in imported_files)

    def _is_valid_file(self, filename):
        valid_extensions = ['.mp3', '.m4a', '.wav', '.vtt', '.txt']
        _, ext = os.path.splitext(filename)
        return ext.lower() in valid_extensions and not filename.startswith('.')

    def _get_file_type(self, filename):
        audio_extensions = ['.mp3', '.m4a', '.wav']
        _, ext = os.path.splitext(filename)
        if ext.lower() in audio_extensions:
            return 'audio'
        elif ext.lower() == '.vtt':
            return 'vtt'
        elif ext.lower() == '.txt':
            return 'text'
        else:
            return 'other'

    def _process_audio_file(self, file_path, audio_dir):
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        wav_filename = f"{name}.wav"
        wav_path = os.path.join(audio_dir, wav_filename)

        if ext.lower() != '.wav':
            print(f"Converting {filename} to WAV format...")
            audio = AudioSegment.from_file(file_path)
            audio.export(wav_path, format="wav")
            print(f"Converted and saved: {wav_filename}")
        else:
            shutil.copy(file_path, wav_path)
            print(f"Copied WAV file: {wav_filename}")

        return filename, wav_filename

    def set_interview_name(self, interviewee_name):
        suggested_name = f"Interview with {interviewee_name}"
        print(f"Suggested interview name: {suggested_name}")
        user_input = input("Press Enter to accept, or type a new name: ").strip()
        return user_input if user_input else suggested_name

    def _process_vtt_file(self, project_name, file_path, original_filename):
        with open(file_path, 'r') as file:
            vtt_content = file.read()

        speakers = self.ppe.extract_speakers(vtt_content)
        print(f"Extracted speakers from {original_filename}:")
        print(f"Interviewee: {speakers['interviewee']}")
        print(f"Interviewer: {speakers['interviewer']}")
        if speakers['other_speakers']:
            print(f"Other speakers: {', '.join(speakers['other_speakers'])}")

        if input("Are these names correct? (Y/n): ").lower() != 'n':
            interview_name = self.set_interview_name(speakers['interviewee'])
            self.data_manager.save_interview_metadata(project_name, None, None, original_filename, speakers, interview_name)
            print(f"Interview name set to: {interview_name}")
            print("Names saved to project metadata.")
        else:
            print("Names not saved. Please update manually later.")

        audio_files = glob.glob(os.path.join(os.path.dirname(file_path), "audio", "*.wav"))
        if audio_files:
            print("Available audio files:")
            for i, audio_file in enumerate(audio_files, 1):
                print(f"{i}. {os.path.basename(audio_file)}")
            choice = input("Enter the number of the corresponding audio file (or press Enter to skip): ")
            if choice.isdigit() and 1 <= int(choice) <= len(audio_files):
                selected_audio = audio_files[int(choice) - 1]
                original_audio = os.path.splitext(os.path.basename(selected_audio))[0] + os.path.splitext(original_filename)[1]
                self.data_manager.associate_audio_with_vtt(project_name, original_filename, original_audio, os.path.basename(selected_audio))
                print(f"Associated {original_audio} with {original_filename}")
            else:
                print("No audio file associated.")
        else:
            print("No audio files found in the project's audio directory.")

    def associate_file_with_interview(self, project_name, filename, interview_name):
        if self.data_manager.associate_file_with_interview(project_name, filename, interview_name):
            print(f"File '{filename}' associated with interview '{interview_name}' in project '{project_name}'.")
        else:
            print(f"Failed to associate file. Project, interview, or file not found.")

    def status(self, project_name):
        project = self.data_manager.get_project_status(project_name)
        if project:
            console = Console()
            
            console.print(f"[bold]Project Name:[/bold] {project['name']}")
            console.print(f"[bold]Principal Investigator:[/bold] {self.get_project_pi(project_name)}")
            console.print("[bold]Learning Goals:[/bold]")
            learning_goals = project.get('learning_goals', [])
            if learning_goals:
                for goal in learning_goals:
                    console.print(Markdown(goal))
            else:
                console.print("No learning goals set")
            
            for interview in project.get('interviews', []):
                console.print(f"\n[bold]{interview.get('name', 'Unnamed Interview')}[/bold]")
                console.print(f"Date: {interview.get('date', 'Not set')}")
                console.print(f"Interviewee: {interview.get('interviewee', 'Not set')}")
                console.print(f"Interviewer: {interview.get('interviewer', 'Not set')}")
                if interview.get('other_speakers'):
                    console.print(f"Other participants: {', '.join(interview['other_speakers'])}")
                
                table = Table(title="Interview Files")
                table.add_column("File Type", style="cyan")
                table.add_column("Path", style="magenta")
                table.add_column("Imported", justify="center")
                table.add_column("Processed", justify="center")
                table.add_column("Analyzed", justify="center")
                
                file_types = ['original_audio_file', 'wav_file', 'vtt_file']
                file_type_names = ['Original Audio', 'Converted Audio', 'Transcription']
                
                for file_type, file_type_name in zip(file_types, file_type_names):
                    file_path = interview.get(file_type, 'Not set')
                    if file_type == 'original_audio_file':
                        file_path = interview.get('original_audio_file', 'Not set')
                    elif file_type == 'wav_file':
                        file_path = interview.get('wav_file', 'Not set')
                
                    imported = '✓' if file_path != 'Not set' else ' '
                    processed = '✓' if interview.get(f'{file_type}_processed', False) else ' '
                    analyzed = '✓' if interview.get(f'{file_type}_analyzed', False) else ' '
                
                    table.add_row(file_type_name, str(file_path), imported, processed, analyzed)
                
                console.print(table)
            
            if project.get('unassociated_files'):
                console.print("\n[bold]Unassociated files:[/bold]")
                for file in project['unassociated_files']:
                    console.print(f"  - {file.get('filename', 'Unnamed File')} ({file.get('file_type', 'Unknown Type')})")
        else:
            console.print(f"Project '{project_name}' does not exist.")

    def list_projects(self):
        projects = self.data_manager.list_projects()
        if projects:
            print("Available projects:")
            for project in projects:
                print(f"  - {project}")
        else:
            print("No projects found.")
