"""
Lineから読み込んだトーク履歴のテキストファイルを読み込み、
csvファイルにして出力する前処理関数
"""
from fileinput import filename
import pandas as pd
from datetime import datetime as dt
import json
import os

class Preprocesser():
    """
    txt_dir: 生データのテキストのディレクトリ
    meta_dir: メタデータのディレクトリ
    id: データid
    """
    def __init__(self, txt_dir, meta_dir, id:int):
        file_name = "raw_" + str(id) + ".txt"
        meta_name = "meta_data.jsonl"
        self.txt_path = os.path.join(txt_dir, file_name)
        self.meta_path = os.path.join(meta_dir, meta_name)
        self.df = pd.DataFrame({})  
        self.text_list = []  # 行を要素する生データのリスト
        self.id = id  # テキストid

    def get_basic_df(self)-> pd.DataFrame:
        """
        基本となるdfを作成し、インスタンス変数として保持
        また、作成したdfを返す
        """
        with open(self.txt_path, 'r') as f:
            self.text_list = f.readlines()
        day_change_row = []  # 日が変わる行数のリスト
        for row,line in enumerate(self.text_list):
            if line == '\n' and self.text_list[row + 1].find('20') == 0:
                day_change_row.append(row)
        
        all_day_list = []  # 全ての日付情報のstrリスト
        time_list = []  # 時間の文字列リスト
        from_list = []  # 誰からのメッセージなのかのリスト
        processed_text_list = []  # 前処理された文章が格納されるリスト
        for i in range(len(day_change_row)):
            if(i != len(day_change_row) - 1):
                day_row = day_change_row[i] + 1  # 日付の行
                day_str = self.text_list[day_row]  # 日付文字列
                day_start = day_row + 1  # 注目日のトークの始まり
                day_end = day_change_row[i + 1]  # 注目日のトークの終わり

                for all_text in self.text_list[day_start:day_end]:  # 注目日のテキストリスト
                    text_per_time = all_text.split(sep='\t')  # 送信時間ごとに分割
                    #  改行されている同一テキストの連結
                    if(len(text_per_time) == 1):
                        processed_text_list[-1] = \
                        processed_text_list[-1] + \
                        text_per_time[0].replace("\n","").replace("\"", "")
                    else:
                        time_list.append(text_per_time[0])
                        from_list.append(text_per_time[1])
                        all_day_list.append(day_str.replace('\n', ''))
                        processed_text_list.append(
                            text_per_time[2].replace('\n', '').replace("\"", ""))

        self.df['full_day'] = all_day_list
        self.df['time'] = time_list
        self.df['from'] = from_list
        self.df['text'] = processed_text_list

    def __getlength__(self):
        return len(self.df)

    def add_each_time(self):
        """
        文字列の日付データを分解し、数値として扱いやすくする。
        また、Unix時間に変換することで時間の演算を可能にする
        """
        year_list = []
        month_list = []
        day_list = []
        unix_stamp = []

        for full_day in self.df['full_day']:
            tmp = full_day.split('/')
            year_list.append(int(tmp[0]))
            month_list.append(int(tmp[1]))
            day_list.append(int(tmp[2][0:2]))
        self.df['year'] = year_list
        self.df['month'] = month_list
        self.df['day'] = day_list

        hours_list = []
        minutes_list = []
        for time in self.df['time']:
            hours_list.append(int(time.split(':')[0]))
            minutes_list.append(int(time.split(':')[1]))
        self.df['hour'] = hours_list
        self.df['minute'] = minutes_list
        self.df = self.df[self.df["from"]!='']  # メッセージ取り消しの削除
        self.df = self.df.reset_index()

        # unix時間への変換
        for i in range(len(self.df)):
            dt_obj = dt(self.df.iloc[i]['year'],
            self.df.iloc[i]['month'],
            self.df.iloc[i]['day'],
            self.df.iloc[i]['hour'],
            self.df.iloc[i]['minute'])
            unix_stamp.append(dt_obj.timestamp()
            )
        self.df['unix_stamp'] = unix_stamp

    def add_flags_interval(self):
        """
        メッセージを送っているユーザーが入れ替わったかのフラグと
        会話が終了したと思われるテキストへのフラグを追加
        また、相手のメッセージからの返信時間を追加
        同時に複数のメッセージを送信している場合は、
        それぞれのインターバルは同一のものとする
        """
        change_speaker_list = [] # 話し手が切り替わる行
        start_talk_list = []  # 会話が終了したと考えられる行
        for i in range(len(self.df)):
            if self.df.iloc[i-1]['from'] != self.df.iloc[i]['from'] and i !=0 :
                change_speaker_list.append(True)
            else:
                change_speaker_list.append(False)
            # 2日返信がなければ、会話が終了していると判断
            if (self.df.iloc[i]['day'] - self.df.iloc[i-1]['day'] > 1) and i !=0 :
                start_talk_list.append(True)
            else:
                start_talk_list.append(False)
        self.df['change_speaker'] = change_speaker_list
        self.df['start_talk'] = start_talk_list

        # インターバルの追加
        # 話者が切り替わっていて、会話が終わっていない場合のみインターバルを計算
        # 複数のトークを1度に送信している場合、先頭の時間を参照する
        pre_pointer = 0
        current_pointer = 0
        interval = 0
        interval_list = []
        for change_flag, start_flag in zip(change_speaker_list,start_talk_list):
            if change_flag and (start_flag==False):
                interval = self.df['unix_stamp'][current_pointer]\
                    - self.df['unix_stamp'][pre_pointer]
                pre_pointer = current_pointer
            if start_flag:
                interval = 0
            interval_list.append(interval/3600)
            current_pointer += 1    
        self.df['interval[h]'] = interval_list
                    
    def save_as_csv(self, out_dir='./processed_data'):
        # 前処理済みデータをcsvで書き出し
        name = "processed_" + str(self.id) + ".csv"
        out_path = os.path.join(out_dir, name)
        self.df.to_csv(out_path,index=None, encoding='utf-8')

    def dump_jsonl(self, data, output_path, append=False):
        """
        Write list of objects to a JSON lines file.
        """
        mode = 'a+' if append else 'w'
        with open(output_path, mode, encoding='utf-8') as f:
            for line in data:
                json_record = json.dumps(line, ensure_ascii=False)
                f.write(json_record + '\n')

    def load_jsonl(self, input_path, has_index=True) -> list:
        """
        Read list of objects from a JSON lines file.
        """
        data = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if has_index:
                    json_l = json.loads(line.rstrip('\n|\r'))
                    # hack ... 
                    v = list(json_l.values())[0]
                    data.append(v)
                else:
                    data.append(json.loads(line.rstrip('\n|\r')))
        return data

    def save_meta_data(self):
        # 名前やファイルなどのメタデータをjsonで書き出し
        target_name = self.text_list[0][7:-8]
        name = list(self.df['from'].unique())
        name.remove(target_name)
        save_date = self.text_list[1][5:-7]
        save_time = self.text_list[1][-6:-1]
        meta_dict = {
            "id": self.id,
            "file_path": self.txt_path,
            "usr_name": name[0],
            "target_name": target_name,
            "save_date": save_date,
            "save_time": save_time
        }
        json_list = self.load_jsonl(self.meta_path, has_index=False)
        json_list.append(meta_dict)
        self.dump_jsonl(json_list, self.meta_path)

    def do_all_preprocess(self):
        df = self.get_basic_df()
        self.add_each_time()
        self.add_flags_interval()
        self.save_as_csv()
        self.save_meta_data()

def test_func():
    preprocesser = Preprocesser('./raw_data',
     "./meta_data", id = 0)
    preprocesser.do_all_preprocess()
    preprocesser.save_meta_data()

if __name__=='__main__':
     test_func()