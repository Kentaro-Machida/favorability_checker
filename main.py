from src.favorability_check import FavorabilityGetter
from src.preprocess import Preprocesser
from src.radar_chart import RadarMaker
from src.dir_existing_check import check_and_make_dir

import os
import uuid
from datetime import datetime
from flask import Flask, flash, request, redirect, url_for, jsonify

RAW_DIR = "./data/raw_data"  # 生の文章があるディレクトリ
META_FILE = "./data/meta_data/meta_data.jsonl"  # メタデータがあるディレクトリ
SCORE_FILE = "./data/score_output/score.jsonl"  # スコアを記録していくjsonl
RADER_DIR = "./data/rader_images/"  # レーダーチャートを記録するディレクトリ
PROCESSED_DIR = "./data/processed_data"  # 前処理を行った後のデータを貯蔵するディレクトリ

# アプリケーション
ALLOWED_EXTENSIONS = {'txt'}  # 許可する拡張子

app = Flask(__name__)
app.secret_key="testkey"
app.config['UPLOAD_FOLDER'] = RAW_DIR
app.config["JSON_AS_ASCII"] = False

"""
名前を解析し、危ないファイルでないかを確認
"""
def allowed_file(filename:str)->bool:
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # postリクエストにファイルがくっついているかを確認する
        # request.filesは、辞書でデータを管理している
        if 'file' not in request.files:
            flash('No file part')
            return "error: there is no file."
        file = request.files['file']
        # ファイルがなかった際の動作
        if file.filename == '':
            flash('No selected file') # ファイルがない旨をユーザーに伝える
            return "error: there is no request."
        # ファイルがあり、許された拡張子だった場合の処理
        if file and allowed_file(file.filename):
            # ファイルがアップロードされた時間をregister_timeに格納
            dt = datetime.today()
            parts = [str(dt.year), str(dt.month) \
                , str(dt.day), str(dt.hour), str(dt.minute), str(dt.second)]
            register_time = ""
            for i, part in enumerate(parts):
                if i != len(parts) - 1:
                    register_time += part
                    register_time += '_'
                else:
                    register_time += part
            
            # ディレクトリ、ファイルの存在確認(なかったら作成)
            check_and_make_dir(
                [
                    RAW_DIR,
                    META_FILE,
                    RADER_DIR,
                    PROCESSED_DIR,
                    SCORE_FILE
                ])

            # データに対して一意なidを発行
            data_id = str(uuid.uuid4())
            filename = 'raw_' + data_id + '.txt'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # 生のテキストから前処理済みのcsvを作成
            preprocesser = Preprocesser(txt_dir=RAW_DIR,\
                 meta_path=META_FILE, id=data_id, out_dir=PROCESSED_DIR)
            preprocesser.do_all_preprocess()
            meta_dict = preprocesser.get_meta_dict()  # ユーザのメタデータを取得

            # 前処理したデータから高感度スコア等を取得
            getter = FavorabilityGetter(id=data_id, meta_dict=meta_dict,\
                    output_json_path=SCORE_FILE, input_csv_dir=PROCESSED_DIR, )
            result = getter.all_caluculate()

            rader = RadarMaker(SCORE_FILE, id=data_id, rader_dir=RADER_DIR)
            rader.saver_radar()
            
            return jsonify(result)
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

if __name__=='__main__':
    app.run()
