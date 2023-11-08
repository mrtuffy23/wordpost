import os
from os.path import join, dirname
from flask import Flask, render_template, request, jsonify, redirect, url_for
from pymongo import MongoClient
from datetime import date
from dotenv import load_dotenv
import requests

app = Flask(__name__)

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

@app.route('/')
def main():
    words_result = db.words.find({}, {'_id': False})
    words = []
    for word in words_result:
        definition = word['definitions'][0]['shortdef']
        definition = definition if type(definition) is str else definition[0]
        words.append({
            'word': word['word'],
            'definition': definition
        })
    msg = request.args.get('msg')
    return render_template("index.html", words=words, msg=msg)


@app.route('/detail/<keyword>')
def detail(keyword):
    api_key = 'ad0d4a0a-709d-4616-8756-85324b223667'
    root_url = 'https://www.dictionaryapi.com/api/v3/references/collegiate/json'
    final_url = f'{root_url}/{keyword}?key={api_key}'
    r = requests.get(final_url)
    result = r.json()

    if not result:
        return redirect(url_for(
            'error_handling',
            word=keyword,
        ))

    if type(result[0]) is str:
        result = ','.join(result)
        return redirect(url_for(
            'error_handling',
            word=keyword,
            suggestions=result
        ))

    return render_template(
        "detail.html",
        word=keyword,
        definitions=result,
        is_old=request.args.get('is_old', False)
    )

@app.route('/error')
def error_handling():
    word = request.args.get('word')
    suggestions = request.args.get('suggestions')
    return render_template(
        'error.html',
        word=word,
        suggestions=suggestions
    )

@app.route('/api/save_word', methods=['POST'])
def save_word():
    json_data = request.get_json()
    word = json_data.get('word')
    definitions = json_data.get('definitions')
    doc = {
        'word': word,
        'definitions': definitions,
        'date': str(date.today()),
        'ex_sentences': []
    }

    db.words.insert_one(doc)
    return jsonify({
        'result': 'success',
        'msg': f'The word "{word}" was saved!'
    })


@app.route('/api/delete_word', methods=['POST'])
def delete_word():
    word = request.form.get('word')
    db.words.delete_one({'word': word})
    return jsonify({
        'result': 'success',
        'msg': f'The word "{word}" was deleted!'
    })

@app.route('/api/save_ex', methods=['POST'])
def save_ex():
    word = request.form.get('word')
    ex = request.form.get('sentence')
    ex_id = str(id(ex))
    db.words.update_one({ 'word': word },
        {
            '$push': {
                'ex_sentences': {
                    'id': ex_id,
                    'sentence': ex
                }
            }
        }
    )
    return jsonify({
        'msg': 'Successfully add ex word!'
    })


@app.route('/api/get_ex', methods=['GET'])
def get_ex():
    word = request.args.get('word')
    ex_stc = db.words.aggregate([
        { '$match': { 'word': word } },
        { '$project': { '_id': False, 'ex_sentences': True } }
    ])
    ex_stc = list(ex_stc)

    return ex_stc


@app.route('/api/delete_ex', methods=['POST'])
def delete_ex():
    word = request.form.get('word')
    id = request.form.get('id')
    db.words.update_one({ 'word': word }, {
        '$pull': {
            'ex_sentences': {
                'id': id
            }
        } },
        False,
    )

    return jsonify({
        'msg': 'data terhapus'
    })

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
