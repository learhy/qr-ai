import anthropic
from plm.plm import ProjectLifecycleManager
import urllib.parse
import logging
import json
import logging

class AnalysisEngine:
    def __init__(self, plm: ProjectLifecycleManager):
        self.plm = plm
        if plm.anthropic_api_key:
            self.client = anthropic.Client(api_key=plm.anthropic_api_key)
        else:
            print("Warning: Anthropic API key not found in configuration.")
            self.client = None

    def analyze_interviews(self, project_name, argument):
        learning_goals = self.plm.get_learning_goals(project_name)
        interviews = self.plm.get_interview_data(project_name, argument)

        for interview in interviews:
            vtt_filename = urllib.parse.unquote(interview['vtt_file'])
            vtt_content = self.plm.get_vtt_content(project_name, vtt_filename)
            if vtt_content is None:
                logging.error(f"Unable to analyze interview {interview['index']}: VTT file not found or unreadable")
                continue
            analysis_results = self.analyze_single_interview(vtt_content, learning_goals)
            self.plm.data_manager.save_analysis_results(project_name, interview['index'], analysis_results)
            print(f"Analysis completed for interview {interview['index']}")

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
