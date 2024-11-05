import subprocess

import flask

app = flask.Flask(__name__)


@app.route('/')
def index():
    return 'Simple Client for OpenHands'


@app.route('/execute', methods=['POST'])
def execute():
    try:
        data = flask.request.json
        command = data.get('command')
        for editor in ['nano', 'vi', 'vim', 'pico', 'joe', 'emacs']:
            if f'{editor} ' in command:
                output = f'Use non interactive command to edit files with {editor}'
                break
        else:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            output, error = proc.communicate(timeout=10)
        output += '\nec2@ip $ '
        return flask.jsonify({'result': 'success', 'output': output})
    except Exception as e:
        return flask.jsonify({'result': 'error', 'output': str(e)})


if __name__ == '__main__':
    app.run(debug=0, host='0.0.0.0', port=5000)
