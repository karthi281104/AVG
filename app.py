from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/gold')
def gold_rate():
    return render_template('gold_rate.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name')
    return f"Hello, {name}!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

