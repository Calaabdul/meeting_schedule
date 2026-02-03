import os

import logging
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s',
    datefmt= '%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url="http://localhost:11434/v1")
model = 'llama3.2'



class EventExtraction(BaseModel):
    description: str = Field(description='description of the meering or event')
    is_calendar_event: bool = Field(description='whether the text describes a calendar event')
    confidence_score: float= Field(description='Confidence score of whether is it calendar event or not', ge=0, le=1)

class EventDetails(BaseModel):
    name: str = Field(description='name of event or meeting')
    date: str = Field(description='Date and time of the event')
    duration:int= Field(description="Duration of event in hours and minutes")
    participants: list[str] = Field(description='Names of participant of the event')

class EventConfirmation(BaseModel):
    confirmation_message:str =Field(description='Natural languagae confirmation message')
    calendar_link: str | None = Field(default = None, description="calendar link if provided")


def extract_event_info(user_input:str) -> EventExtraction:
    today = datetime.now()

    response = client.chat.completions.parse(
        model = model,
        messages = [
            {'role': 'system',
             'content': 'Analyze the input request, determine whether it is a calendar or meeting event and return the description if it is true'},
             {'role': 'user', 
              'content': user_input},
        ],
        response_format=EventExtraction,
    )

    result = response.choices[0].message.parsed
    logger.info(f'is it a calendar event? {result.is_calendar_event}')
    return result



def parse_event_details(description:str) -> EventDetails:
    today = datetime.now()

    response = client.chat.completions.parse(
        model = model,
        messages = [
            {'role': 'system',
             'content': 'Extract all event details from the description including date, time and participants'},
             {'role': 'user',
              'content': description}

        ],
        response_format = EventDetails
    )

    result = response.choices[0].message.parsed

    return result


def generate_confirmation_message(event_details: EventDetails) -> EventConfirmation:
    response= client.chat.completions.parse(
        model = model,
        messages = [
            {'role': 'system',
             'content': 'Generate confirmation message of atleast 3 sentences consisting of all the details in the event details'},
             {'role': 'user',
              'content': str(event_details.model_dump())}
              ],
        temperature = 1.5,
        response_format = EventConfirmation
    )

    result = response.choices[0].message.parsed

    return result



def process_meeting_request(user_input: str) -> Optional[EventConfirmation]:

    """Main orchestration of the prompt chain with gate check"""
    first_extraction = extract_event_info(user_input)

    if (
        not first_extraction.is_calendar_event
        and first_extraction.confidence_score < 0.7
        ):
        logger.warning(f'Gate check failed; is_calendar_event: {first_extraction.is_calendar_event}')
        return None
    

    event_details = parse_event_details(first_extraction.description)

    confirmation = generate_confirmation_message(event_details)

    logging.info('Calendar event succesfully created')
    return confirmation


 
user_input = "Can you schedule an office meeting of 1 hour:30 minutes, on the 30th of January with my friend, John Doe"
result = process_meeting_request(user_input)
if result:
    print(f'Confirmation sucess: {result.confirmation_message}')
    if result.calendar_link:
        print(f'Calendar link: {result.calendar_link}')
else:
    print('This is not a Calendar event!!')