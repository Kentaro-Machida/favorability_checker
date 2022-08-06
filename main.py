from favorability_check import FavorabilityGetter
from preprocess import Preprocesser
from radar_chart import RadarMaker

raw_dir = "./raw_data"  # 生の文章があるディレクトリ
meta_dir = "./meta_data"  # メタデータがあるディレクトリ
score_file = "./score_output/score.jsonl"
id = '0-test'  # データID

pre = Preprocesser(txt_dir=raw_dir, meta_dir=meta_dir, id=id)
pre.do_all_preprocess()
getter = FavorabilityGetter(id=id)
getter.all_caluculate()
rader = RadarMaker(score_file, id=id)
rader.saver_radar()


