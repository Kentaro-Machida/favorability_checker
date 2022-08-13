import os

def check_and_make_dir(check_list:list):
    """
    ターゲットディレクトリと存在確認したいディレクトリのリストを受け取り、
    存在確認したいディレクトリが存在していなければ、ディレクトリを作成する
    """
    for target_path in check_list:
        split = target_path.split("/")

        if not os.path.exists(target_path):
            # 対象がファイルの場合
            if split[-1].find(".") > 0:
                target_dir = ""
                for i,w in enumerate(split):
                    if i == len(split) -1:
                        break
                    target_dir += w
                    target_dir += "/"
                os.makedirs(target_dir)
                f = open(target_path, "w")
                f.close()
            # 対象がフォルダの場合
            else:
                os.makedirs(target_path)

