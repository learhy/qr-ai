import re
from collections import Counter

class PreprocessorEngine:
    def __init__(self):
        pass

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
