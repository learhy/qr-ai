import json
import os
import configparser
import urllib.parse

class DataManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self._load_data()

    def _load_data(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                return json.load(f)
        return {"projects": []}

    def _save_data(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def create_project(self, project_name, principal_investigator):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                return False
        new_project = {
            "name": project_name,
            "directory": os.path.join(os.getcwd(), "project_data", project_name),
            "principal_investigator": principal_investigator,
            "learning_goals": "",
            "interviews": [],
            "unassociated_files": []
        }
        self.data["projects"].append(new_project)
        self._save_data()
        
        # Create project directory if it doesn't exist
        os.makedirs(new_project["directory"], exist_ok=True)
        
        return True

    def get_project_config(self, project_name):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                config = configparser.ConfigParser()
                config_path = os.path.join(os.getcwd(), "project_data", project_name, 'project.conf')
                config.read(config_path)
                return config
        return None

    def get_project_pi(self, project_name):
        project_config = self.get_project_config(project_name)
        if project_config:
            return project_config.get('Project', 'principal_investigator', fallback=None)
        return None

    def save_project_config(self, project_name, config):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                config_path = os.path.join(os.getcwd(), "project_data", project_name, 'project.conf')
                with open(config_path, 'w') as configfile:
                    config.write(configfile)
                return True
        return False

    def set_learning_goal(self, project_name, raw_goal, preprocessed_goals):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                project["learning_goals"] = {
                    "raw": raw_goal,
                    "preprocessed": preprocessed_goals
                }
                self._save_data()
                return True
        return False

    def get_learning_goals(self, project_name):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                return project.get("learning_goals", {})
        return {}

    def create_interview(self, project_name, interview_data):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                interviews = project.setdefault("interviews", [])
                new_index = max([interview.get("index", 0) for interview in interviews] + [0]) + 1
                new_interview = {
                    "index": new_index,
                    "name": interview_data.get("name", f"Interview {new_index}"),
                    "interviewee": interview_data.get("interviewee", "Not set"),
                    "interviewer": interview_data.get("interviewer", "Not set"),
                    "date": interview_data.get("date", "Not set"),
                    "description": interview_data.get("description", ""),
                    "original_audio_file": interview_data.get("original_audio_file"),
                    "wav_file": interview_data.get("wav_file"),
                    "vtt_file": interview_data.get("vtt_file"),
                    "other_speakers": interview_data.get("other_speakers", []),
                    "files": interview_data.get("files", [])
                }
                interviews.append(new_interview)
                self._save_data()
                return new_interview
        return None

    def update_interview(self, project_name, interview_name, interview_data):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                for interview in project.get("interviews", []):
                    if interview["name"] == interview_name:
                        interview.update(interview_data)
                        self._save_data()
                        return interview
        return None

    def get_interview(self, project_name, interview_name):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                for interview in project.get("interviews", []):
                    if interview["name"] == interview_name:
                        return interview
        return None

    def import_file(self, project_name, filename, file_type, interview_name=None):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                new_file = {"filename": filename, "file_type": file_type}
                if interview_name:
                    for interview in project["interviews"]:
                        if interview["name"] == interview_name:
                            interview["files"].append(new_file)
                            self._save_data()
                            return True
                else:
                    project["unassociated_files"].append(new_file)
                    self._save_data()
                    return True
        return False

    def associate_file_with_interview(self, project_name, filename, interview_name):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                file_to_move = None
                for file in project["unassociated_files"]:
                    if file["filename"] == filename:
                        file_to_move = file
                        break
                if file_to_move:
                    project["unassociated_files"].remove(file_to_move)
                    for interview in project["interviews"]:
                        if interview["name"] == interview_name:
                            interview["files"].append(file_to_move)
                            self._save_data()
                            return True
        return False

    def get_project_status(self, project_name):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                # Ensure all necessary fields are present
                for interview in project.get("interviews", []):
                    for file_type in ['original_audio_file', 'wav_file', 'vtt_file']:
                        if file_type not in interview:
                            interview[file_type] = 'Not set'
                        interview[f'{file_type}_processed'] = interview.get(f'{file_type}_processed', False)
                return project
        return None

    def list_projects(self):
        return [project["name"] for project in self.data["projects"]]

    def save_interview_metadata(self, project_name, original_audio_filename, wav_filename, vtt_filename, speakers, interview_name):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                if "interviews" not in project:
                    project["interviews"] = []
                project["interviews"].append({
                    "name": interview_name,
                    "original_audio_file": urllib.parse.unquote(original_audio_filename),
                    "wav_file": urllib.parse.unquote(wav_filename),
                    "vtt_file": urllib.parse.unquote(vtt_filename),
                    "interviewee": speakers["interviewee"],
                    "interviewer": speakers["interviewer"],
                    "other_speakers": speakers["other_speakers"]
                })
                self._save_data()
                return True
        return False

    def associate_audio_with_vtt(self, project_name, vtt_filename, original_audio_filename, wav_filename):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                for interview in project.get("interviews", []):
                    if interview["vtt_file"] == vtt_filename:
                        interview["original_audio_file"] = original_audio_filename
                        interview["wav_file"] = wav_filename
                        self._save_data()
                        return True
        return False

    def update_audio_files(self, project_name, original_audio, wav_audio):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                if "audio_files" not in project:
                    project["audio_files"] = []
                project["audio_files"].append({
                    "original_audio_file": original_audio,
                    "wav_file": wav_audio
                })
                self._save_data()
                return True
        return False

    def associate_latest_audio_with_vtt(self, project_name, vtt_filename):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                if "audio_files" in project and project["audio_files"]:
                    latest_audio = project["audio_files"][-1]
                    for interview in project.get("interviews", []):
                        if interview["vtt_file"] == vtt_filename:
                            interview["original_audio_file"] = latest_audio["original_audio_file"]
                            interview["wav_file"] = latest_audio["wav_file"]
                            self._save_data()
                            return True
        return False

    def get_imported_files(self, project_name):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                imported_files = set()
                for interview in project.get("interviews", []):
                    if "original_audio_file" in interview:
                        imported_files.add(os.path.splitext(interview["original_audio_file"])[0])
                    if "vtt_file" in interview:
                        imported_files.add(os.path.splitext(interview["vtt_file"])[0])
                return imported_files
        return set()

    def get_learning_goals(self, project_name):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                return project.get("learning_goals", {})
        return {}

    def get_interview_data(self, project_name, interview_index=None):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                if interview_index is None or interview_index == 'all':
                    return project.get("interviews", [])
                else:
                    return [interview for interview in project.get("interviews", []) if interview["index"] == int(interview_index)]
        return []

    def save_analysis_results(self, project_name, interview_index, analysis_results):
        for project in self.data["projects"]:
            if project["name"] == project_name:
                for interview in project["interviews"]:
                    if interview["index"] == interview_index:
                        interview["analysis_results"] = analysis_results
                        self._save_data()
                        return True
        return False
