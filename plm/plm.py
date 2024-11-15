import os
import configparser
from .data_manager import DataManager
from ppe.ppe import PreprocessorEngine
from ae.ae import AnalysisEngine
import shutil
from pydub import AudioSegment
import glob
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
import urllib.parse
import logging
import shutil

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

        # Read Anthropic API key from config
        self.anthropic_api_key = self.global_config.get('Anthropic', 'api_key', fallback=None)
        self.anthropic_model = self.global_config.get('Anthropic', 'model', fallback='claude-3-5-sonnet-20241022')
        self.anthropic_max_tokens = self.global_config.getint('Anthropic', 'max_tokens', fallback=4000)
        self.anthropic_temperature = self.global_config.getfloat('Anthropic', 'temperature', fallback=0.7)

        # Initialize AnalysisEngine
        self.ae = AnalysisEngine(self.data_manager, self.anthropic_api_key, self.anthropic_max_tokens)

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
        preprocessed_goals = self.ppe.get_preprocessed_learning_goals(goal)
        
        preprocessed_goals_dict = [
            {
                'index': goal.index,
                'content': goal.content
            } for goal in preprocessed_goals
        ]
        
        if self.data_manager.set_learning_goal(project_name, goal, preprocessed_goals_dict):
            print(f"Learning goals set for project '{project_name}'.")
            print("Note: Each line and each sentence within a line is treated as an individual learning goal.")
            print("Learning goals have been preprocessed and stored.")
        else:
            print(f"Project '{project_name}' does not exist.")

    def set_interview(self, project_name, interview_name, interviewee, interviewer, date, description):
        interview_data = {
            "name": interview_name,
            "interviewee": interviewee,
            "interviewer": interviewer,
            "date": date,
            "description": description
        }
        existing_interview = self.data_manager.get_interview(project_name, interview_name)
        if existing_interview:
            interview = self.data_manager.update_interview(project_name, interview_name, interview_data)
            print(f"Interview '{interview_name}' updated for project '{project_name}'.")
        else:
            interview = self.data_manager.create_interview(project_name, interview_data)
            print(f"Interview '{interview_name}' created for project '{project_name}'.")
        
        return interview_name if interview else None

    def import_files(self, project_name):
        project_dir = os.getcwd()
        project_data_dir = os.path.join(project_dir, "project_data", project_name)
        audio_dir = os.path.join(project_data_dir, "audio")
        vtt_dir = os.path.join(project_data_dir, "vtt")  # New directory for VTT files
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(vtt_dir, exist_ok=True)  # Create VTT directory

        files = [f for f in os.listdir(project_dir) if os.path.isfile(os.path.join(project_dir, f)) and self._is_valid_file(f)]
        if not files:
            print(f"No valid files found in the project directory: {project_dir}")
            return

        # Sort files by file type (extension)
        sorted_files = sorted(files, key=lambda x: self._get_file_type(x))

        imported_files = self.data_manager.get_imported_files(project_name)
        files_to_import = [f for f in sorted_files if not self._is_file_imported(f, imported_files)]

        if not files_to_import:
            print("No new files to import.")
            return

        print("Available files to import:")
        for i, file in enumerate(files_to_import, 1):
            print(f"{i}. {file}")

        while True:
            choice = input("\nEnter the numbers of files to import (comma-separated), 'all' for all files, or press Enter to exit: ").strip().lower()
            
            if choice == '':
                print("Import process cancelled.")
                return
            elif choice == 'all':
                files_to_process = files_to_import
                break
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in choice.split(',')]
                    files_to_process = [files_to_import[i] for i in indices if 0 <= i < len(files_to_import)]
                    if not files_to_process:
                        print("No valid files selected. Please try again.")
                    else:
                        break
                except ValueError:
                    print("Invalid input. Please enter numbers, 'all', or press Enter to exit.")

        audio_files = [f for f in files_to_process if self._get_file_type(f) == 'audio']
        vtt_files = [f for f in files_to_process if self._get_file_type(f) == 'vtt']

        print("Converting audio files to WAV format...")
        converted_audio_files = []
        for file in audio_files:
            file_path = os.path.join(project_dir, file)
            original_filename, wav_filename = self._process_audio_file(file_path, audio_dir)
            converted_audio_files.append((original_filename, wav_filename))
            self.data_manager.update_audio_files(project_name, original_filename, wav_filename)

        print("\nProcessing VTT files...")
        for file in vtt_files:
            src_path = os.path.join(project_dir, file)
            dst_path = os.path.join(vtt_dir, file)
            shutil.copy2(src_path, dst_path)  # Copy VTT file to project data directory
            self._process_vtt_file(project_name, dst_path, file)
            # Associate the most recently added audio file with this VTT file
            self.data_manager.associate_latest_audio_with_vtt(project_name, file)

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
        # Ensure we're using the unquoted filename
        original_filename = urllib.parse.unquote(original_filename)
        with open(file_path, 'r', encoding='utf-8') as file:
            vtt_content = file.read()

        speakers = self.ppe.extract_speakers(vtt_content)
        print(f"Extracted speakers from {original_filename}:")
        print(f"Interviewee: {speakers['interviewee']}")
        print(f"Interviewer: {speakers['interviewer']}")
        if speakers['other_speakers']:
            print(f"Other speakers: {', '.join(speakers['other_speakers'])}")

        if input("Are these names correct? (Y/n): ").lower() != 'n':
            interview_name = self.set_interview_name(speakers['interviewee'])
            interview_data = {
                "name": interview_name,
                "vtt_file": original_filename,
                "interviewee": speakers['interviewee'],
                "interviewer": speakers['interviewer'],
                "other_speakers": speakers['other_speakers']
            }
            self.data_manager.create_interview(project_name, interview_data)
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
                self.data_manager.update_interview(project_name, interview_name, {
                    "original_audio_file": original_audio,
                    "wav_file": os.path.basename(selected_audio)
                })
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

    def preprocess_and_save_interview(self, project_name, interview):
        vtt_filename = interview.get('vtt_file')
        if vtt_filename:
            raw_content = self.get_vtt_content(project_name, vtt_filename)
            if raw_content:
                processed_content = self.ppe.preprocess_vtt_content(raw_content)
                raw_tokens = self.ae._estimate_token_count(raw_content)
                processed_tokens = self.ae._estimate_token_count(processed_content)
                
                # Save processed content and token counts
                self.data_manager.update_interview(project_name, interview['name'], {
                    'processed_vtt_content': processed_content,
                    'raw_tokens': raw_tokens,
                    'processed_tokens': processed_tokens
                })
                return raw_tokens, processed_tokens
        return 0, 0

    def status(self, project_name):
        project = self.data_manager.get_project_status(project_name)
        if project:
            console = Console()
            
            console.print(f"[bold]Project Name:[/bold] {project['name']}")
            console.print(f"[bold]Principal Investigator:[/bold] {self.get_project_pi(project_name)}")
            
            console.print("\n[bold]Learning Goals:[/bold]")
            self.show_preprocessed_learning_goals(project_name)
            
            if project.get('interviews'):
                console.print("\n[bold]Interviews:[/bold]")
                interviews_table = Table(show_header=True, header_style="bold magenta")
                interviews_table.add_column("Index", style="dim", width=5)
                interviews_table.add_column("Name", style="dim", width=20)
                interviews_table.add_column("Date")
                interviews_table.add_column("Interviewee")
                interviews_table.add_column("Interviewer")
                interviews_table.add_column("Other Participants")
                interviews_table.add_column("Analyzed", justify="center")
                interviews_table.add_column("Raw Tokens", justify="right")
                interviews_table.add_column("Processed Tokens", justify="right")

                for interview in project['interviews']:
                    if 'raw_tokens' not in interview or 'processed_tokens' not in interview:
                        raw_tokens, processed_tokens = self.preprocess_and_save_interview(project_name, interview)
                    else:
                        raw_tokens = interview['raw_tokens']
                        processed_tokens = interview['processed_tokens']

                    interviews_table.add_row(
                        str(interview['index']),
                        interview.get('name', 'Unnamed Interview'),
                        interview.get('date', 'Not set'),
                        interview.get('interviewee', 'Not set'),
                        interview.get('interviewer', 'Not set'),
                        ', '.join(interview.get('other_speakers', [])) or 'None',
                        '✓' if interview.get('analysis_results') else ' ',
                        str(raw_tokens),
                        str(processed_tokens)
                    )

                console.print(interviews_table)

                console.print("\n[bold]Interview Files:[/bold]")
                files_table = Table(show_header=True, header_style="bold magenta")
                files_table.add_column("Index", style="dim", width=5)
                files_table.add_column("Interview", style="dim", width=20)
                files_table.add_column("File Type")
                files_table.add_column("Path")
                files_table.add_column("Imported", justify="center")
                files_table.add_column("Pre-Processed", justify="center")
                files_table.add_column("Analyzed", justify="center")

                file_types = ['original_audio_file', 'wav_file', 'vtt_file']
                file_type_names = ['Original Audio', 'Converted Audio', 'Transcription']

                file_index = 1
                for interview in project['interviews']:
                    for file_type, file_type_name in zip(file_types, file_type_names):
                        file_path = interview.get(file_type, 'Not set')
                        imported = '✓' if file_path != 'Not set' else ' '
                        processed = '✓' if interview.get(f'{file_type}_processed', False) else ' '
                        analyzed = '✓' if interview.get('analysis_results') else ' '

                        files_table.add_row(
                            str(file_index),
                            interview.get('name', 'Unnamed Interview'),
                            file_type_name,
                            str(file_path),
                            imported,
                            processed,
                            analyzed
                        )
                        file_index += 1

                console.print(files_table)
            
            if project.get('unassociated_files'):
                console.print("\n[bold]Unassociated files:[/bold]")
                unassociated_table = Table(show_header=True, header_style="bold magenta")
                unassociated_table.add_column("Filename")
                unassociated_table.add_column("File Type")

                for file in project['unassociated_files']:
                    unassociated_table.add_row(
                        file.get('filename', 'Unnamed File'),
                        file.get('file_type', 'Unknown Type')
                    )

                console.print(unassociated_table)
        else:
            console.print(f"Project '{project_name}' does not exist.")

    def get_learning_goals(self, project_name):
        return self.data_manager.get_learning_goals(project_name)

    def get_interview_data(self, project_name, interview_index=None):
        return self.data_manager.get_interview_data(project_name, interview_index)

    def get_vtt_content(self, project_name, vtt_filename):
        project_dir = os.path.join(os.getcwd(), "project_data", project_name)
        vtt_dir = os.path.join(project_dir, "vtt")
        # Use urllib.parse.unquote to handle URL-encoded filenames
        vtt_filename = urllib.parse.unquote(vtt_filename)
        vtt_path = os.path.join(vtt_dir, vtt_filename)
        try:
            with open(vtt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            logging.error(f"VTT file not found: {vtt_path}")
            return None
        except Exception as e:
            logging.error(f"Error reading VTT file {vtt_path}: {str(e)}")
            return None

    def perform_meta_analysis(self, project_name):
        from ae.ae import AnalysisEngine
        analysis_engine = AnalysisEngine(self.data_manager, self.anthropic_api_key, self.anthropic_max_tokens)
        return analysis_engine.perform_meta_analysis(project_name)

    def get_meta_analysis_results(self, project_name):
        return self.data_manager.get_meta_analysis_results(project_name)

    def table_status(self, project_name):
        project = self.data_manager.get_project_status(project_name)
        if project:
            console = Console()
            table = Table(title=f"Project Status: {project['name']}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="magenta")

            table.add_row("Project Name", project['name'])
            table.add_row("Principal Investigator", self.get_project_pi(project_name))

            learning_goals = project.get('learning_goals', {})
            if learning_goals:
                raw_goals = learning_goals.get('raw', 'No raw learning goals set')
                table.add_row("Raw Learning Goals", raw_goals[:50] + "..." if len(raw_goals) > 50 else raw_goals)
                
                preprocessed_goals = learning_goals.get('preprocessed', [])
                if preprocessed_goals:
                    goals_summary = "\n".join([f"- {goal['content']}" for goal in preprocessed_goals])
                    table.add_row("Preprocessed Learning Goals", goals_summary[:50] + "..." if len(goals_summary) > 50 else goals_summary)
            else:
                table.add_row("Learning Goals", "No learning goals set")

            for interview in project.get('interviews', []):
                table.add_row(
                    str(interview['index']),  # This will now always be present
                    interview.get('name', 'Unnamed Interview'),
                    interview.get('date', 'Not set'),
                    interview.get('interviewee', 'Not set'),
                    interview.get('interviewer', 'Not set'),
                    ', '.join(interview.get('other_speakers', [])) or 'None'
                )
                
                for file_type in ['original_audio_file', 'wav_file', 'vtt_file']:
                    file_path = interview.get(file_type, 'Not set')
                    table.add_row(f"{file_type.replace('_', ' ').title()}", file_path)

            if project.get('unassociated_files'):
                unassociated = ", ".join([f"{file['filename']} ({file['file_type']})" for file in project['unassociated_files']])
                table.add_row("Unassociated files", unassociated)

            console.print(table)
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

    def show_preprocessed_learning_goals(self, project_name):
        project = self.data_manager.get_project_status(project_name)
        if project:
            learning_goals = project.get('learning_goals', {})
            if learning_goals and learning_goals.get('preprocessed'):
                console = Console()
                table = Table(title="Preprocessed Learning Goals")
                table.add_column("Index", style="cyan", no_wrap=True)
                table.add_column("Learning Goal", style="magenta")

                for goal in learning_goals['preprocessed']:
                    table.add_row(str(goal['index']), goal['content'])
                    if 'children' in goal:
                        for subgoal in goal['children']:
                            table.add_row(f"  {subgoal['index']}", subgoal['content'])

                console.print(table)
            else:
                print("No learning goals set for this project.")
        else:
            print(f"Project '{project_name}' does not exist.")
