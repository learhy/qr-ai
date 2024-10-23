import anthropic
import urllib.parse
import logging
import json
import itertools
import threading
import time
import sys
import os
from typing import List, Dict

class AnalysisEngine:
    def __init__(self, data_manager, anthropic_api_key, anthropic_max_tokens):
        self.data_manager = data_manager
        self.anthropic_api_key = anthropic_api_key
        self.anthropic_max_tokens = anthropic_max_tokens
        if anthropic_api_key:
            self.client = anthropic.Client(api_key=anthropic_api_key)
        else:
            print("Warning: Anthropic API key not found in configuration.")
            self.client = None
        self.spinner_thread = None

    def spinner(self):
        spinner = itertools.cycle(['-', '/', '|', '\\'])
        while getattr(self.spinner_thread, "do_run", True):
            sys.stdout.write(next(spinner))
            sys.stdout.flush()
            sys.stdout.write('\b')
            time.sleep(0.1)

    def start_spinner(self):
        self.spinner_thread = threading.Thread(target=self.spinner)
        self.spinner_thread.daemon = True
        self.spinner_thread.start()

    def stop_spinner(self):
        if self.spinner_thread:
            self.spinner_thread.do_run = False
            self.spinner_thread.join()
            sys.stdout.write(' ')
            sys.stdout.flush()

    def analyze_interviews(self, project_name, argument):
        learning_goals = self.data_manager.get_learning_goals(project_name)
        interviews = self.data_manager.get_interview_data(project_name, argument)

        for interview in interviews:
            print(f"Analyzing interview {interview['index']}... ", end="", flush=True)
            self.start_spinner()
            
            vtt_filename = urllib.parse.unquote(interview['vtt_file'])
            vtt_content = self.get_vtt_content(project_name, vtt_filename)
            if vtt_content is None:
                self.stop_spinner()
                logging.error(f"Unable to analyze interview {interview['index']}: VTT file not found or unreadable")
                continue
            analysis_results = self.analyze_single_interview(vtt_content, learning_goals)
            self.data_manager.save_analysis_results(project_name, interview['index'], analysis_results)
            
            self.stop_spinner()
            print(f"Analysis completed for interview {interview['index']}")

    def get_vtt_content(self, project_name, vtt_filename):
        project_dir = os.path.join(os.getcwd(), "project_data", project_name)
        vtt_dir = os.path.join(project_dir, "vtt")
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

    def analyze_single_interview(self, vtt_content, learning_goals):
        prompt = self.create_analysis_prompt(vtt_content, learning_goals)
        response = self.submit_for_analysis(prompt)
        parsed_results = self.parse_analysis_response(response)
        return self._post_process_results(parsed_results)

    def _post_process_results(self, results):
        for result in results:
            if not result['evidence']:
                result['evidence'] = [{
                    'timestamp': 'N/A',
                    'quote': 'No specific quote available',
                    'explanation': 'Insufficient information in the transcript to provide evidence.'
                }]
            if not result['confidence']:
                result['confidence'] = 'Low'
            if not result['answer'] or result['answer'] == 'Not enough data to answer':
                result['answer'] = 'Insufficient information to answer'
        return results

    def create_analysis_prompt(self, vtt_content, learning_goals):
        prompt = f"""
        You are an expert qualitative researcher tasked with analyzing the following interview transcript. Your goal is to provide insightful, evidence-based answers to each learning goal question. Follow these guidelines strictly:

        1. Analyze the interview transcript thoroughly.
        2. For each learning goal, provide a comprehensive answer based solely on the information in the transcript.
        3. ALWAYS include at least one piece of evidence for each learning goal, even if it's to explain why there isn't enough information.
        4. If the transcript doesn't contain sufficient information to answer a learning goal, state "Insufficient information to answer" as the answer.
        5. ALWAYS provide a confidence level (High, Medium, or Low) for each learning goal, based on the available evidence.
        6. Avoid making assumptions or introducing information not present in the transcript.
        7. Be concise but thorough in your answers.

        Interview Transcript:
        {vtt_content}

        Learning Goals:
        {self.format_learning_goals(learning_goals)}

        Provide your analysis in the following format for each learning goal:

        [Learning Goal X: Title]
        Answer: (Provide a comprehensive answer here, or state "Insufficient information to answer" if applicable)
        Evidence:
        - Timestamp: (HH:MM:SS)
          Quote: "(Exact quote from the transcript)"
          Explanation: (Brief explanation of how this quote supports your answer or why there isn't enough information)
        Confidence: (High/Medium/Low - based on the amount and quality of supporting evidence)

        Repeat this structure for each learning goal, ensuring that every goal has an answer, at least one piece of evidence, and a confidence rating.
        """
        return prompt

    def format_learning_goals(self, learning_goals):
        return "\n".join([f"{i+1}. {goal['content']}" for i, goal in enumerate(learning_goals['preprocessed'])])

    def parse_analysis_response(self, response):
        parsed_results = []
        current_goal = None
        current_answer = {}

        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('[Learning Goal'):
                if current_goal:
                    self._finalize_current_answer(current_answer)
                    parsed_results.append(current_answer)
                current_goal = line
                current_answer = {'learning_goal': current_goal, 'answer': '', 'evidence': [], 'confidence': ''}
            elif line.startswith('Answer:'):
                current_answer['answer'] = line.replace('Answer:', '').strip()
            elif line.startswith('Evidence:'):
                continue  # Skip this line, we'll collect evidence in the following lines
            elif line.startswith('- Timestamp:'):
                evidence = {'timestamp': line.replace('- Timestamp:', '').strip()}
                current_answer['evidence'].append(evidence)
            elif line.startswith('Quote:') and current_answer['evidence']:
                current_answer['evidence'][-1]['quote'] = line.replace('Quote:', '').strip()
            elif line.startswith('Explanation:') and current_answer['evidence']:
                current_answer['evidence'][-1]['explanation'] = line.replace('Explanation:', '').strip()
            elif line.startswith('Confidence:'):
                current_answer['confidence'] = line.replace('Confidence:', '').strip()

        if current_goal:  # Add the last goal
            self._finalize_current_answer(current_answer)
            parsed_results.append(current_answer)

        return parsed_results

    def perform_meta_analysis(self, project_name: str) -> List[Dict]:
        print("Performing meta-analysis... ", end="", flush=True)
        self.start_spinner()

        project_data = self.data_manager.get_project_status(project_name)
        learning_goals = self.data_manager.get_learning_goals(project_name)
        
        interviews = self.data_manager.get_interview_data(project_name)
        
        # Break analysis into chunks
        chunk_results = self._analyze_in_chunks(project_name, interviews, learning_goals)
        
        # Combine chunk results
        meta_analysis_results = self._combine_chunk_results(chunk_results, learning_goals)
        
        self.data_manager.save_meta_analysis_results(project_name, meta_analysis_results)
        
        self.stop_spinner()
        print("Meta-analysis completed!")
        return meta_analysis_results

    def _get_all_transcripts(self, project_name: str) -> str:
        interviews = self.data_manager.get_interview_data(project_name)
        return "\n\n".join([self.get_vtt_content(project_name, interview['vtt_file']) for interview in interviews if 'vtt_file' in interview])

    def _get_analyzable_interviews(self, interviews: List[Dict], project_name: str) -> List[Dict]:
        analyzable_interviews = []
        current_tokens = 0
        for interview in interviews:
            interview_transcript = self.get_vtt_content(project_name, interview['vtt_file'])
            interview_tokens = self._estimate_token_count(interview_transcript)
            if current_tokens + interview_tokens <= self.anthropic_max_tokens:
                analyzable_interviews.append(interview)
                current_tokens += interview_tokens
            else:
                break
        return analyzable_interviews

    def _get_transcripts_for_interviews(self, project_name: str, interviews: List[Dict]) -> str:
        return "\n\n".join([self.get_vtt_content(project_name, interview['vtt_file']) for interview in interviews if 'vtt_file' in interview])

    def _analyze_in_chunks(self, project_name: str, interviews: List[Dict], learning_goals: Dict) -> List[Dict]:
        chunk_results = []
        current_chunk = []
        current_tokens = 0

        for interview in interviews:
            interview_transcript = self.get_vtt_content(project_name, interview['vtt_file'])
            interview_tokens = self._estimate_token_count(interview_transcript)
            
            if current_tokens + interview_tokens > self.anthropic_max_tokens:
                if current_chunk:
                    chunk_results.append(self._analyze_chunk(current_chunk, learning_goals))
                current_chunk = [interview_transcript]
                current_tokens = interview_tokens
            else:
                current_chunk.append(interview_transcript)
                current_tokens += interview_tokens
        
        if current_chunk:
            chunk_results.append(self._analyze_chunk(current_chunk, learning_goals))
        
        return chunk_results

    def _analyze_chunk(self, chunk: List[str], learning_goals: Dict) -> Dict:
        all_transcripts = "\n\n".join(chunk)
        prompt = self._create_meta_analysis_prompt(learning_goals, all_transcripts)
        response = self.submit_for_analysis(prompt)
        return self.parse_meta_analysis_response(response)

    def _combine_chunk_results(self, chunk_results: List[Dict], learning_goals: Dict) -> List[Dict]:
        combined_results = []
        
        for goal in learning_goals['preprocessed']:
            goal_results = []
            for chunk in chunk_results:
                for result in chunk:
                    if result['learning_goal'] == f"[Learning Goal {goal['index']}]":
                        goal_results.append(result)
            
            combined_result = self._synthesize_goal_results(goal, goal_results)
            combined_results.append(combined_result)
        
        return combined_results

    def _synthesize_goal_results(self, goal: Dict, goal_results: List[Dict]) -> Dict:
        prompt = f"""
        Synthesize the following results for the learning goal: "{goal['content']}"

        Results:
        {json.dumps(goal_results, indent=2)}

        Provide a synthesized answer that combines insights from all chunks, a confidence score (0-100) based on the consistency and quality of evidence across chunks, and the most relevant pieces of evidence.

        Format your response as follows:
        Answer: (Your synthesized answer)
        Confidence: (0-100)
        Evidence:
        1. Quote: "(Most relevant quote)"
           Context: (Interview context)
           Explanation: (How this supports the answer)
        2. (Second most relevant piece of evidence)
        3. (Third most relevant piece of evidence)
        """

        response = self.submit_for_analysis(prompt)
        synthesized_result = self.parse_meta_analysis_response(response)[0]
        synthesized_result['learning_goal'] = f"[Learning Goal {goal['index']}]"
        return synthesized_result

    def calculate_interview_tokens(self, project_name: str, interview: Dict) -> int:
        vtt_filename = interview.get('vtt_file')
        if vtt_filename:
            vtt_content = self.get_vtt_content(project_name, vtt_filename)
            if vtt_content:
                return self._estimate_token_count(vtt_content)
        return 0

    def _estimate_token_count(self, text: str) -> int:
        if self.client:
            return self.client.count_tokens(text)
        else:
            # Fallback to rough estimation if client is not available
            return len(text) // 4

    def _create_meta_analysis_prompt(self, learning_goals, all_transcripts):
        goals_text = self.format_learning_goals(learning_goals)
        return f"""You are an expert qualitative researcher tasked with performing a comprehensive analysis of the provided interview transcripts. Your goal is to synthesize information from these transcripts to answer the following learning goals:

        {goals_text}

        Follow these guidelines to conduct a thorough and insightful analysis:

        1. Carefully analyze all provided transcripts, identifying patterns, themes, and connections.
        2. For each learning goal, provide:
           a) A comprehensive answer that synthesizes information from all relevant transcripts.
           b) A confidence score (0-100) based on the consistency and quality of evidence in the provided transcripts.
           c) At least three pieces of supporting evidence, including:
              - Direct quotes from the transcripts (with interview context)
              - Explanation of how each piece of evidence supports your answer
        3. If there are conflicting viewpoints or experiences across interviews, analyze and explain these differences.
        4. Consider the frequency and emphasis of certain topics across interviews, and how this impacts your conclusions.

        Ensure your analysis is:
        - Comprehensive: Utilize information from all relevant transcripts
        - Objective: Base your conclusions solely on the provided data
        - Nuanced: Capture the complexity of the topics discussed
        - Well-supported: Provide clear links between your conclusions and the evidence

        Here are the interview transcripts for this chunk:

        {all_transcripts}

        Please provide your detailed analysis, structuring your response for each learning goal as follows:

        [Learning Goal X]
        Answer: (Your comprehensive synthesis)
        Confidence: (0-100)
        Evidence:
        1. Quote: "(Direct quote)"
           Context: (Interview context)
           Explanation: (How this supports your answer)
        2. (Repeat for at least 3 pieces of evidence)

        Begin your analysis:
        """

    def parse_meta_analysis_response(self, response):
        parsed_results = []
        current_goal = None
        current_answer = {}

        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('[Learning Goal'):
                if current_goal:
                    parsed_results.append(current_answer)
                current_goal = line
                current_answer = {'learning_goal': current_goal, 'answer': '', 'evidence': [], 'confidence': ''}
            elif line.startswith('Answer:'):
                current_answer['answer'] = line.replace('Answer:', '').strip()
            elif line.startswith('Confidence:'):
                current_answer['confidence'] = line.replace('Confidence:', '').strip()
            elif line.startswith('Evidence:'):
                continue  # Skip this line, we'll collect evidence in the following lines
            elif line.startswith('- Quote:'):
                evidence = {'quote': line.replace('- Quote:', '').strip()}
                current_answer['evidence'].append(evidence)
            elif line.startswith('Context:') and current_answer['evidence']:
                current_answer['evidence'][-1]['context'] = line.replace('Context:', '').strip()

        if current_goal:  # Add the last goal
            parsed_results.append(current_answer)

        return parsed_results

    def _finalize_current_answer(self, answer):
        if not answer['evidence']:
            answer['evidence'] = [{
                'timestamp': 'N/A',
                'quote': 'No specific quote available',
                'explanation': 'Insufficient information in the transcript to provide evidence.'
            }]
        if not answer['confidence']:
            answer['confidence'] = 'Low'
        if not answer['answer']:
            answer['answer'] = 'Insufficient information to answer'

    def submit_for_analysis(self, text):
        if not self.client:
            return "Analysis failed: Anthropic API key not configured."
        try:
            response = self.client.messages.create(
                model=self.plm.anthropic_model,
                messages=[{"role": "user", "content": text}],
                max_tokens=self.plm.anthropic_max_tokens,
                temperature=self.plm.anthropic_temperature,
            )
            raw_response = response.content[0].text
            logging.debug(f"Raw LLM response: {raw_response}")
            return raw_response
        except Exception as e:
            logging.error(f"Error during analysis: {str(e)}")
            return "Analysis failed due to an error."

    def refine_analysis(self, analysis, feedback):
        try:
            response = self.client.messages.create(
                model=self.plm.anthropic_model,
                messages=[
                    {"role": "user", "content": f"Here's an analysis:\n\n{analysis}\n\nPlease refine this analysis based on the following feedback:\n\n{feedback}"}
                ],
                max_tokens=self.plm.anthropic_max_tokens,
                temperature=self.plm.anthropic_temperature,
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error during analysis refinement: {str(e)}")
            return "Analysis refinement failed due to an error."

    def ask_question(self, analysis, question):
        try:
            response = self.client.messages.create(
                model=self.plm.anthropic_model,
                messages=[
                    {"role": "user", "content": f"Given this analysis:\n\n{analysis}\n\nPlease answer the following question:\n\n{question}"}
                ],
                max_tokens=self.plm.anthropic_max_tokens,
                temperature=self.plm.anthropic_temperature,
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error while answering question: {str(e)}")
            return "Failed to answer the question due to an error."
