from favorability_check import FavorabilityGetter
from preprocess import Preprocesser
from radar_chart import RadarMaker

id = 1

pre = Preprocesser(txt_dir="./raw_data", meta_dir="./meta_data", id=id)
pre.do_all_preprocess()
getter = FavorabilityGetter(id = id)
getter.all_caluculate()
rader = RadarMaker("./score_output/score.jsonl", id=id)
rader.saver_radar()


