import re
import spacy
from typing import List, Dict, Any
from dataclasses import dataclass
from collections import defaultdict

# Optional dependencies with graceful fallback
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:
    def TfidfVectorizer(*args, **kwargs):
        # Dummy fallback implementation
        class DummyVectorizer:
            def fit_transform(self, texts):
                return texts
            def get_feature_names_out(self):
                return []
        return DummyVectorizer(*args, **kwargs)
@dataclass
class LearningGoal:
    content: str
    index: int

class PreprocessorEngine:
    def __init__(self):
        self.learning_goals = []
        self.nlp = spacy.load("en_core_web_sm")  # Load the pre-trained NER model

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

    def discover_entities(self, text: str) -> Dict[str, List[str]]:
        config = {
            'window_size': 5,
            'min_entity_length': 3,
            'context_threshold': 0.75,
            'similarity_eps': 0.5
        }
        
        # Comprehensive Tech Keywords (using the previous implementation)
        TECH_KEYWORDS = {
            # Cloud Ecosystem
            'cloud': {
                'primary': ['cloud computing', 'cloud infrastructure', 'cloud services'],
                'providers': ['aws', 'amazon web services', 'azure', 'google cloud', 'gcp', 
                            'oracle cloud', 'alibaba cloud', 'digital ocean', 'heroku'],
                'models': ['iaas', 'paas', 'saas', 'serverless', 'hybrid cloud', 'multi-cloud'],
                'technologies': ['containerization', 'cloud migration', 'cloud native']
            },
            
            # Cybersecurity Domains
            'cybersecurity': {
                'primary': ['information security', 'network security', 'cyber defense'],
                'practices': ['penetration testing', 'vulnerability assessment', 'threat hunting', 
                            'security audit', 'incident response', 'risk management'],
                'technologies': ['firewall', 'intrusion detection', 'encryption', 'zero trust', 
                                'siem', 'endpoint protection', 'dns security'],
                'compliance': ['gdpr', 'hipaa', 'pci dss', 'iso 27001', 'nist']
            },
            
            # Software Development Ecosystem
            'software_development': {
                'paradigms': ['agile', 'scrum', 'kanban', 'extreme programming', 'lean development'],
                'methodologies': ['devops', 'ci/cd', 'test-driven development', 'behavior-driven development'],
                'version_control': ['git', 'github', 'gitlab', 'bitbucket', 'svn'],
                'architectures': ['microservices', 'monolithic', 'serverless', 'event-driven']
            },
            
            # Artificial Intelligence and Machine Learning
            'ai_ml': {
                'primary': ['artificial intelligence', 'machine learning', 'deep learning'],
                'subfields': ['natural language processing', 'computer vision', 'reinforcement learning', 
                            'generative ai', 'predictive analytics'],
                'technologies': ['neural networks', 'transformer models', 'gpt', 'large language models', 
                                'convolutional neural networks', 'recurrent neural networks'],
                'frameworks': ['tensorflow', 'pytorch', 'keras', 'scikit-learn', 'openai']
            },
            
            # Data Technologies
            'data_technologies': {
                'databases': {
                    'relational': ['postgresql', 'mysql', 'oracle', 'sql server', 'sqlite'],
                    'nosql': ['mongodb', 'cassandra', 'redis', 'dynamodb', 'couchdb'],
                    'data_warehouses': ['snowflake', 'bigquery', 'redshift']
                },
                'data_processing': ['apache spark', 'hadoop', 'etl', 'data pipeline', 'apache kafka'],
                'analytics': ['tableau', 'power bi', 'data visualization', 'business intelligence']
            },
            
            # Networking and Infrastructure
            'networking': {
                'protocols': ['tcp/ip', 'http', 'https', 'dns', 'dhcp', 'ssl/tls'],
                'network_types': ['wan', 'lan', 'vpn', 'sd-wan', 'edge network'],
                'hardware': ['router', 'switch', 'firewall', 'load balancer', 'network appliance']
            },
            
            # Containerization and Orchestration
            'containerization': {
                'primary': ['docker', 'kubernetes', 'container orchestration'],
                'platforms': ['openshift', 'rancher', 'docker swarm', 'amazon eks'],
                'related_technologies': ['helm', 'istio', 'service mesh', 'microservices']
            },
            
            # Web Technologies
            'web_technologies': {
                'frontend': ['react', 'vue.js', 'angular', 'svelte', 'web components'],
                'backend': ['nodejs', 'django', 'flask', 'ruby on rails', 'spring boot'],
                'protocols': ['rest api', 'graphql', 'websockets', 'grpc'],
                'standards': ['html5', 'css3', 'webassembly', 'progressive web apps']
            },
            
            # Emerging and Frontier Technologies
            'emerging_tech': {
                'frontier': ['quantum computing', 'blockchain', 'edge computing', 'augmented reality'],
                'internet_of_things': ['iot', '5g', 'smart devices', 'industrial iot'],
                'advanced_computing': ['neuromorphic computing', 'quantum machine learning']
            },
            
            # Enterprise and Management Technologies
            'enterprise_tech': {
                'erp_crm': ['sap', 'salesforce', 'oracle erp', 'microsoft dynamics'],
                'project_management': ['jira', 'asana', 'trello', 'microsoft project'],
                'collaboration': ['slack', 'microsoft teams', 'zoom', 'confluence']
            }
}

        def flatten_tech_keywords(tech_dict):
            flattened = set()
            
            def recursive_flatten(obj):
                if isinstance(obj, dict):
                    for value in obj.values():
                        recursive_flatten(value)
                elif isinstance(obj, list):
                    for item in obj:
                        recursive_flatten(item)
                elif isinstance(obj, str):
                    flattened.update([
                        obj.lower(), 
                        *obj.lower().split()
                    ])
            
            recursive_flatten(tech_dict)
            return flattened

        COMPREHENSIVE_TECH_KEYWORDS = flatten_tech_keywords(TECH_KEYWORDS)
        
        # Predefined lists for fallback and filtering
        STOPWORDS = {'the', 'a', 'an', 'in', 'on', 'at', 'for', 'of', 'with'}
        ABBREVIATIONS = {'AI', 'IBM', 'API', 'HR', 'IT'}
        
        # Structured entity categories
        entity_categories = {
            'PERSON': set(),
            'ORG': set(),
            'GPE': set(),
            'TECH': set(),
            'ABBREVIATION': set(),
            'NUMBERS': set(),
            'TIME_PERIOD': set(),
            'TIME_UNIT': set()
        }
        
        # SpaCy Named Entity Recognition
        doc = self.nlp(text)
        
        # Extract named entities from SpaCy
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC']:
                category_key = ent.label_ if ent.label_ in entity_categories else 'GPE'
                if len(ent.text) > 2 and ent.text not in STOPWORDS:
                    entity_categories[category_key].add(ent.text)
        
        # Advanced entity extraction
        def extract_candidates():
            # Noun chunks and tokens with specific attributes
            candidates = [
                chunk.text for chunk in doc.noun_chunks 
                if len(chunk.text.split()) <= 3 and 
                chunk.root.pos_ in ['PROPN', 'NOUN']
            ]
            
            # Additional token-based candidates
            candidates.extend([
                token.text for token in doc 
                if (token.pos_ in ['PROPN', 'NOUN']) and 
                len(token.text) > 2 and 
                token.text.lower() not in STOPWORDS
            ])
            
            return list(set(candidates))
        
        # Score and categorize entities
        def score_and_categorize(candidates):
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                vectorizer = TfidfVectorizer(stop_words='english')
                tfidf_matrix = vectorizer.fit_transform([text])
                feature_names = vectorizer.get_feature_names_out()
            except ImportError:
                # Fallback if sklearn not available
                feature_names = text.split()
                def tfidf_fallback(word):
                    return 1.0 if word in feature_names else 0.0
            
            for candidate in candidates:
                words = candidate.lower().split()
                
                # Enhanced Tech term categorization
                if (any(tech in candidate.lower() for tech in COMPREHENSIVE_TECH_KEYWORDS) or 
                    candidate.upper() in ABBREVIATIONS):
                    entity_categories['TECH'].add(candidate)
                
                # Numeric detection
                if candidate.replace(',', '').isdigit():
                    entity_categories['NUMBERS'].add(candidate)
        
        # Time-based extractions
        def extract_temporal_entities():
            time_patterns = [
                (r'\d+\s*(year|years|day|days)', 'TIME_PERIOD'),
                (r'(second|minute|hour|day|week|month|year)', 'TIME_UNIT')
            ]
            
            for pattern, category in time_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entity_categories[category].update(matches)
        
        # Execute extraction stages
        candidates = extract_candidates()
        score_and_categorize(candidates)
        extract_temporal_entities()
        
        # Add abbreviation detection
        entity_categories['ABBREVIATION'].update(
            token.text for token in doc if token.text.isupper() and token.text in ABBREVIATIONS
        )
        
        # Diagnostic information
        entity_categories['_diagnostics'] = {
            'total_tokens': len(doc),
            'entity_distribution': {
                category: len(entities) 
                for category, entities in entity_categories.items() 
                if category != '_diagnostics'
            }
        }
        
        # Convert sets to sorted lists and remove empty categories
        result = {
            k: sorted(list(v)) 
            for k, v in entity_categories.items() 
            if v and k != '_diagnostics'
        }
        result['_diagnostics'] = entity_categories['_diagnostics']
        
        return result
    
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
