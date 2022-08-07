from flask import Flask
app = Flask(__name__)
 
RAW_DIR = "./raw_data"  # 生の文章があるディレクトリ
META_DIR = "./meta_data"  # メタデータがあるディレクトリ
SCORE_FILE = "./score_output/score.jsonl"

# アプリケーション
ALLOWED_EXTENSIONS = {'txt'}  # 許可する拡張子

def test_func():
    return 'test'

@app.route('/', methods=['GET', 'POST'])
def hello():
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''
 
 
## おまじない
if __name__ == "__main__":
    app.run(debug=True)