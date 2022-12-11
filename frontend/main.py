"""
Author: Jehoshaph Akshay Chandran
"""


from flask import Flask, redirect, url_for, render_template


app = Flask(__name__)


@app.route('/')
def home():
    return redirect(url_for('compose'))


@app.route('/compose/')
def compose():
    context = {
        'page_name': 'Mozart',
    }
    return render_template('compose/compose.html', **context)


if __name__ == '__main__':
    app.run(debug=True)
