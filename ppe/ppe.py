import re
from typing import List
from dataclasses import dataclass

@dataclass
class LearningGoal:
    content: str
    index: int

class PreprocessorEngine:
    def __init__(self):
        self.learning_goals = []

    def get_preprocessed_learning_goals(self, learning_goals: str) -> List[LearningGoal]:
        # Split the input text into lines first
        lines = learning_goals.split('\n')
        
        preprocessed_goals = []
        index = 1
        
        for line in lines:
            # Split each line into sentences
            sentences = re.split(r'(?<=[.!?])\s+', line)
            
            for sentence in sentences:
                cleaned_sentence = self._clean_content(sentence)
                if cleaned_sentence:
                    preprocessed_goals.append(LearningGoal(content=cleaned_sentence, index=index))
                    index += 1
        
        return preprocessed_goals

    def _clean_content(self, content: str) -> str:
        # Remove markdown-style formatting and extra whitespace
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Remove bold
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # Remove italic
        # Remove leading numbers and dots (e.g., "1.", "1.1.", etc.)
        content = re.sub(r'^\s*(?:\d+\.)+\s*', '', content)
        return content.strip()

    def set_learning_goals(self, learning_goals: str):
        self.learning_goals = self.get_preprocessed_learning_goals(learning_goals)

    def get_learning_goals(self) -> List[LearningGoal]:
        return self.learning_goals

    def get_flattened_learning_goals(self) -> List[str]:
        return [f"{goal.index}. {goal.content}" for goal in self.learning_goals]

    def get_learning_goals_dict(self) -> List[dict]:
        return [{'index': goal.index, 'content': goal.content} for goal in self.learning_goals]

    def discover_entities(self, text):
        # Stub: Perform automated entity discovery
        print("Discovering entities in text")
        return ["Entity1", "Entity2"]

    def prompt_for_metadata(self):
        # Stub: Prompt user for interview metadata
        print("Prompting user for interview metadata")
        return {
            "interview_name": "Sample Interview",
            "participants": ["John Doe", "Jane Smith"],
            "date": "2024-10-21",
            "company": "ACME Corp"
        }

    def extract_speakers(self, vtt_content):
        # Remove lines containing '-->'
        lines = [line for line in vtt_content.split('\n') if '-->' not in line]
        
        # Extract speaker names
        speaker_pattern = r'^([^:]+):'
        speakers = []
        for line in lines:
            match = re.match(speaker_pattern, line)
            if match:
                speakers.append(match.group(1).strip())
        
        # Count occurrences of each speaker
        from collections import Counter
        speaker_counts = Counter(speakers)
        
        # Sort speakers by count, descending
        sorted_speakers = sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Prepare the result dictionary
        result = {
            "interviewee": sorted_speakers[0][0] if len(sorted_speakers) > 0 else "",
            "interviewer": sorted_speakers[1][0] if len(sorted_speakers) > 1 else "",
            "other_speakers": [speaker for speaker, _ in sorted_speakers[2:]]
        }
        
        return result

    def preprocess_vtt_content(self, vtt_content: str) -> str:
        lines = vtt_content.split('\n')
        processed_lines = []
        current_speaker = None

        # Remove the "WEBVTT" header if present
        if lines and lines[0].strip() == "WEBVTT":
            lines = lines[1:]

        for line in lines:
            # Remove timestamp lines
            if re.match(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', line):
                continue
            
            # Remove leading numbers and spaces
            line = re.sub(r'^\s*\d+\s*', '', line)
            
            # Process speaker labels and utterances
            if ':' in line:
                speaker, utterance = line.split(':', 1)
                if speaker != current_speaker:
                    if processed_lines:
                        processed_lines.append('')  # Add blank line between speakers
                    current_speaker = speaker
                    processed_lines.append(f"{speaker}:{utterance.strip()}")
                else:
                    processed_lines[-1] += f" {utterance.strip()}"
            elif line.strip():
                processed_lines[-1] += f" {line.strip()}"

        # Join processed lines
        processed_content = "\n".join(processed_lines)

        # Remove redundant spaces
        processed_content = re.sub(r'\s+', ' ', processed_content)

        return processed_content
