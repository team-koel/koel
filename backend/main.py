import datetime

from flask import Flask, render_template, request
from flask_cors import CORS, cross_origin

import openai
import os

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
            section_content = section['prompt']
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