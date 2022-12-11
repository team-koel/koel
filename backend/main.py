import datetime

from flask import Flask, render_template, request
from flask_cors import CORS, cross_origin

import openai
import os
import json

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


from google.auth.transport import requests
from google.cloud import datastore
import google.oauth2.id_token

datastore_client = datastore.Client()

def store_time(email, dt):
    entity = datastore.Entity(key=datastore_client.key('User', email, 'visit'))
    entity.update({
        'timestamp': dt
    })

    datastore_client.put(entity)


def fetch_times(email, limit):
    ancestor = datastore_client.key('User', email)
    query = datastore_client.query(kind='visit', ancestor=ancestor)
    query.order = ['-timestamp']

    times = query.fetch(limit=limit)

    return times

# def store_template(template_name, template_json, template_type):
#     """
#     Store a template in the datastore
#     """
#     entity = datastore.Entity(key=datastore_client.key('Template', template_name, 'template_json'))
#     entity.update({
#         'template_json': template_json,
#         'template_type': template_type
#     })

#     entity = datastore.Entity(key=datastore_client.key('Template', template_name, 'template_json'))
#     entity.update({
#         'template_json': template_json
#     })
#     datastore_client.put(entity)


# def fetch_template(template_name):
#     ancestor = datastore_client.key('Template', template_name)
#     query = datastore_client.query(kind='template_json', ancestor=ancestor)
#     template_json = query.fetch(limit=1)
#     return template_json

firebase_request_adapter = requests.Request()

@app.route('/')
def root():
    # Verify Firebase auth.
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    times = None

    if id_token:
        try:
            # Verify the token against the Firebase Auth API. This example
            # verifies the token on each page load. For improved performance,
            # some applications may wish to cache results in an encrypted
            # session store (see for instance
            # http://flask.pocoo.org/docs/1.0/quickstart/#sessions).
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)

            store_time(claims['email'], datetime.datetime.now(tz=datetime.timezone.utc))
            times = fetch_times(claims['email'], 10)

        except ValueError as exc:
            # This will be raised if the token is expired or any other
            # verification checks fail.
            error_message = str(exc)

    return render_template(
        'index.html',
        user_data=claims, error_message=error_message, times=times)

# @app.route('/get-template', methods=['GET'])
# def get_template():
#     data = request.args.to_dict()
#     template_name = data.get('template_name', None)
#     if template_name is None:
#         return "No template name provided", 400
#     template = 

class yaml_like:
    def __init__(self, data):
        self.data = data
        self.current_state = "section"
        self.content_dict = {}
        self.sections = []
    
    def _read(self):
        for line in self.data.splitlines():
                yield line

    def parse(self):
        lines = self._read()
        for line in lines:
            if line.startswith("[section]"):
                if self.current_state == "section":
                    # end of previous section
                    print(self.content_dict)
                    self.sections.append(self.content_dict)
                    self.content_dict = {}
                    continue
            elif "- type:" in line:
                #self.content_dict["type"] = line.split(":")[1].strip()
                continue
            elif "- content:" in line:
                self.content_dict["content"] = line.split("- content:")[1].strip().replace('"', '')
            elif line.strip() == "":
                # something weird
                raise ValueError(f"Something weird happened: {line}")
        self.sections.append(self.content_dict)
        return self.sections
                

@app.route('/generate-template', methods=['POST'])
@cross_origin()
def generate_template():
    print(request.get_data())
    try:
        data = request.get_json()
    except Exception as e:
        print(e)
        return "Invalid JSON", 400
    workflow = data['workflow']
    title = data['title']
    description = data['description']
    document_type = data['type']

    first_section_prompt = data['sections'][0]['prompt']

    PROMPT = \
f"""
# example configuration describing an email/poster with different sections
# the configuration file should end after the last section
# currently, the only supported section type Text

# example configuration describing an email/poster with different sections
# the configuration file should end after the last section

[poster]
    - Workflow: Wedding Invite
    - Title: Kate and Adam's Wedding
    - Description: A poster for Kate and Adam's wedding indicating the name of the couple, date, time, venue, RSVP email, gifting to charity
    - num_sections: 10
    - supported_section_types: ["Text"]
[section]
    - type: "Text"
    - content: "Together with their families"
[section]
    - type: "Text"
    - content: "Kate and Adam"
[section]
    - type: "Text"
    - content: "Invite you to their wedding on"
[section]
    - type: "Text"
    - content: "Saturday, the twenty-fifth of July"
[section]
    - type: "Text"
    - content: "Two Thousand and Twenty"
[section]
    - type: "Text"
    - content: "At six o'clock in the evening"
[section]
    - type: "Text"
    - content: "The Grand Hotel, New York"
[section]
    - type: "Text"
    - content: "RSVP to kate@gmail.com or 404-524-1234"
[section]
    - type: "Text"
    - content: "In lieu of gifts, please consider donating to the charity of your choice."

[{document_type}]
    - Workflow: {workflow}
    - Title: {title}
    - Description: {description}
    - num_sections: 10
    - supported_section_types: ["Text"]
[section]
"""
    response = openai.Completion.create(
                model="text-davinci-003",
                prompt=PROMPT,
                temperature=0.7,
                max_tokens=839,
                top_p=1,
                frequency_penalty=0.17,
                presence_penalty=0,
                stop=["\n\n"]
    )

    response_text = response['choices'][0]['text']
    print(PROMPT + response_text)
    # parse the response
    sections = []
    try:
        parser = yaml_like(response_text)
        sections = parser.parse()
        print({"sections": sections})
        return {"sections": sections}, 200
    except Exception as e:
        print(e)
        return "Error parsing response", 400


@app.route('/generate', methods=['POST'])
@cross_origin()
def generate_content():
    data = request.get_json()

    workflow = data['workflow']
    title = data['title']
    description = data['description']
    document_type = data['type']

    prompted_section = int(data['get_response'])

    PROMPT_HEADER = \
f"""
[{document_type}]
    - Workflow: {workflow}
    - Title: {title}
    - Description: {description}
"""
    PROMPT_SECTION = \
"""
[section]
    - type: "%(type)s"
    - size: "H1"
    - content: "%(content)s"
"""
    sections = []
    for idx, section in enumerate(data['sections']):
        section_type = section['type']
        if idx == prompted_section:
            section_content = "[insert]"
        else:
            section_content = section['selected_content']
        sections.append(PROMPT_SECTION % {'type': section_type, 'content': section_content})
    
    PROMPT_FOOTER = "Suggest 10 alternative content options for replacing the [insert] tag. The options should be separated by a newline. Do not include the [insert] tag in the options."
    
    prompt = PROMPT_HEADER + "\n" + "\n".join(sections) + "\n" + PROMPT_FOOTER
    print(prompt)
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0.7,
        max_tokens=839,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    response_options = response['choices'][0]['text'].split("\n")
    print(response_options)
    response_options = [option.strip() for option in response_options if option.strip()]

    return {'options': response_options}, 200



if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)