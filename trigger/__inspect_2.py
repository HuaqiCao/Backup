import matplotlib.pyplot as plt
import numpy as np

def __read():
    # 文件路径和名称
    FilePath = str('/mnt/d/storage/research/RUN2408_data_ana/1cmLMO_SB13_T6at8p5mK_bkg_9h20min_5kHz_2408232128/')
    FileName = str('1cmLMO_SB13_T6at8p5mK_bkg_9h20min_5kHz_2408232128.BIN2')
    # startp_file = str('/mnt/d/storage/research/RUN2408_data_ana/1cmLMO_SB13_T6at8p5mK_bkg_9h20min_5kHz_2408232128/data/cutsignalpos3.txt')  # 指定startp值的txt文件路径
    startp_file = str('/mnt/d/storage/research/RUN2408_data_ana/LD_SB13_T6at8p5mK_bkg_9h20min_5kHz_2408232128/data/signalPos2.txt')
        # 读取startp列表
    with open(startp_file, 'r') as f:
        startp_list = [int(line.strip()) for line in f.readlines()]

    print(FilePath + FileName)
    opfile = open(FilePath + FileName, "rb")
    wl = 3000  # 读取的长度

    # 设置图形对象
    fig, ax = plt.subplots(figsize=(10, 6))

    # 遍历startp列表
    for startp in startp_list:
        x = []
        opfile.seek(4 * (startp-500), 0)
        for num in range(0, wl):
            data = int.from_bytes(opfile.read(4), "little", signed=False)
            x.append(data)
        arr_x = np.array(x, dtype=np.float64)

        # # 多项式拟合去除基线
        # p = np.polyfit(np.arange(len(arr_x)), arr_x, deg=0)  # 常数拟合
        # baseline_fit = np.polyval(p, np.arange(len(arr_x)))
        # arr_x = arr_x - baseline_fit

        arr_t = 0.0002 * np.arange(wl)
        # 使用scatter绘制数据点，透明度设置为0.5，颜色统一为蓝色
        ax.scatter(arr_t, arr_x, color='blue', alpha=0.05, s=1)  # s=1设置点的大小
        # ax.set_ylim([4.2949E9+40000, 4.2949E9+65000])  # 自动设置y轴范围


    # 设置图形属性
    ax.set_xlabel('Time (second)', fontsize=15)
    ax.set_ylabel('Amplitude (ADC)', fontsize=15)
    ax.grid(True)

    # 显示图像
    plt.show()

    return

__read()
