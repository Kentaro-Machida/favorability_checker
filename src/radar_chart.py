import matplotlib.pyplot as plt
import numpy as np
import japanize_matplotlib
from .json_function import load_jsonl

class RadarMaker():
    def __init__(self,score_path:str ,id:str):
        self.id = id
        self.score_path = score_path

    def plot_polar(self ,labels, values, imgname):
        angles = np.linspace(0, 2 * np.pi, len(labels) + 1, endpoint=True)
        values = np.concatenate((values, [values[0]]))  # 閉じた多角形にする
        fig = plt.figure()
        ax = fig.add_subplot(111, polar=True)
        ax.set_theta_zero_location('N')
        ax.plot(angles, values, 'o-')  # 外枠
        ax.fill(angles, values, alpha=0.25)  # 塗りつぶし
        ax.set_thetagrids(angles[:-1] * 180 / np.pi, labels)  # 軸ラベル
        ax.set_rlim(0 ,100)
        fig.savefig(imgname)
        plt.close(fig)

    """
    項目ごとのスコア計算を行う。
    """
    def talk_balance_score(self ,data_dict:dict, up_thresh=52, low_thresh=46)->int:
        """
        メッセージ数のバランスを100点満点で評価する。
        自分率: low_thresh% ~ up_thresh% 100点
        この範囲からx離れるごとにx^2ずつ得点が減少する
        """
        target_count = data_dict["message_count"][data_dict["target_name"]]
        usr_count = data_dict["message_count"][data_dict["usr_name"]]

        target_rate = int(100*target_count / (usr_count + target_count))
        if target_rate >= up_thresh:
            return np.max([100 - (np.abs(target_rate - up_thresh))^2, 0])
        elif target_rate <= low_thresh:
            return np.max([100 - (np.abs(target_rate - low_thresh))^2, 0])
        else:
            return 100

    def talk_frequency_score(self ,data_dict:dict, up_thresh=55, low_thresh=0)->int:
        """
        メッセージ間のインターバルの平均値からスコアを算出
        100 * (相手) / (自分) + (相手)の値が
        0 ~ 55 までなら100点
        そこからx離れるごとにx*x^(1/2)ずつスコアが減少
        """
        target_interval = data_dict["interval_average"][data_dict["target_name"]]
        usr_interval = data_dict["interval_average"][data_dict["usr_name"]]

        target_rate = int(100*target_interval/(target_interval + usr_interval))
        if target_rate >= up_thresh:
            return np.max([0, 100 - 0.7*(target_rate - up_thresh)*np.sqrt(target_rate - up_thresh)])
        elif target_rate <= low_thresh:
            return np.max([0, 100-0.7*(low_thresh - target_rate)*np.sqrt(low_thresh - target_rate)])
        else:
            return 100

    def talk_length_score(self ,data_dict:dict, up_thresh=100, low_thresh=45)->int:
        """
        メッセージの文字数のバランスからスコアを算出
        100 * (相手) / (自分) + (相手)の値が
        45 ~ 100 までなら100点
        そこからx離れるごとにx^2ずつスコアが減少
        """
        target_count = data_dict["length"][data_dict["target_name"]]
        usr_count = data_dict["length"][data_dict["usr_name"]]

        target_rate = int(100*target_count / (usr_count + target_count))
        if target_rate >= up_thresh:
            return np.max([100 - (np.abs(target_rate - up_thresh))^2, 0])
        elif target_rate <= low_thresh:
            return np.max([100 - (np.abs(target_rate - low_thresh))^2, 0])
        else:
            return 100

    def question_score(self ,data_dict:dict, up_thresh=100, low_thresh=45)->int:
        """
        質問の割合からスコア算出
        100 * (相手) / (自分) + (相手)の値が
        0 ~ 55 までなら100点
        そこからx離れるごとにx*x^(1/2)ずつスコアが減少
        """
        target_question = data_dict["question"][data_dict["target_name"]]
        usr_question = data_dict["question"][data_dict["usr_name"]]

        target_rate = int(100*target_question/(target_question + usr_question))
        if target_rate >= up_thresh:
            return np.max([0, 100 - (target_rate - up_thresh)*np.sqrt(target_rate - up_thresh)])
        elif target_rate <= low_thresh:
            return np.max([0, 100-(low_thresh - target_rate)*np.sqrt(low_thresh - target_rate)])
        else:
            return 100

    def start_score(self, data_dict:dict, up_thresh=100, low_thresh=55)->int:
        """
        会話を始めた回数からスコア算出
        100 * (相手) / (自分) + (相手)の値が
        55 ~ 100 までなら100点
        そこからx離れるごとにx*x^(1/2)ずつスコアが減少
        """
        target_start = data_dict["talk_start_count"][data_dict["target_name"]]
        usr_start = data_dict["talk_start_count"][data_dict["usr_name"]]

        target_rate = int(100*target_start/(target_start + usr_start))
        if target_rate >= up_thresh:
            return np.max([0, 100 - (target_rate - up_thresh)*np.sqrt(target_rate - up_thresh)])
        elif target_rate <= low_thresh:
            return np.max([0, 100-(low_thresh - target_rate)*np.sqrt(low_thresh - target_rate)])    
        else:
            return 100

    def good_feeling_score(self, data_dict:dict, max_length=5):
        """
        脈ありワードの個数によって得点をつける
        デートか何かのお誘いで80点
        恋人等の確認で20点
        """
        score = 0
        date_count = len(data_dict['asking_date'])
        if date_count >= max_length:
            score += 80
        else:
            score += int(80 * date_count / max_length)

        lovers_check = len(data_dict['lovers_check'])
        if lovers_check != 0:
            score += 20
        return score

    def saver_radar(self):
        data_dict = load_jsonl(self.score_path, has_index=False)[-1]
        values = []
        values.append(self.good_feeling_score(data_dict))
        values.append(self.talk_balance_score(data_dict))
        values.append(self.talk_frequency_score(data_dict))
        values.append(self.talk_length_score(data_dict))
        values.append(self.question_score(data_dict))
        values.append(self.start_score(data_dict))
        labels = ['脈ありワード','会話バランス', '頻度', "文の長さ", '質問', '会話開始']
        name = "radar_" + str(self.id)
        self.plot_polar(labels, values,"./data/sample_images/" + name + ".png")

def test():
    score_path = './score_output/score.jsonl'
    maker = RadarMaker(score_path=score_path,id = 0)
    maker.saver_radar()

if __name__ == '__main__':
    test()