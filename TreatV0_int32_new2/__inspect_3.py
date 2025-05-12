import matplotlib.pyplot as plt
import numpy as np

def __read():
    # 第一个文件路径和名称
    FilePath2 = str('/mnt/d/storage/research/RUN2408_data_ana/LD_SB13_T6at8p5mK_bkg_9h20min_5kHz_2408232128/')
    FileName2 = str('LD_SB13_T6at8p5mK_bkg_9h20min_5kHz_2408232128.BIN2')
    
    # 第二个文件路径和名称
    FilePath1 = str('/mnt/d/storage/research/RUN2408_data_ana/1cmLMO_SB13_T6at8p5mK_bkg_9h20min_5kHz_2408232128/')
    FileName1 = str('1cmLMO_SB13_T6at8p5mK_bkg_9h20min_5kHz_2408232128.BIN2')

    # 第一个文件的startp文件路径
    # startp_file2 = startp_file1 = str('/mnt/d/storage/research/RUN2408_data_ana/SB13_T6at8p5mK_bkg_9h20min_5kHz_2408232128/IsLightCut.txt')
    startp_file2 = startp_file1 = str('/mnt/d/storage/research/RUN2408_data_ana/SB13_T6at8p5mK_bkg_9h20min_5kHz_2408232128/IsLightCut_strict.txt')

    # # 第二个文件的startp文件路径
    # startp_file2 = str('/path/to/startp2.txt')

    # 读取第一个文件的startp列表
    with open(startp_file1, 'r') as f1:
        startp_list1 = [int(line.strip()) for line in f1.readlines()]

    # 读取第二个文件的startp列表
    with open(startp_file2, 'r') as f2:
        startp_list2 = [int(line.strip()) for line in f2.readlines()]

    # 打开两个文件
    opfile1 = open(FilePath1 + FileName1, "rb")
    opfile2 = open(FilePath2 + FileName2, "rb")
    
    wl = 3000  # 读取的长度

    # 设置图形对象
    fig, ax = plt.subplots(figsize=(10, 6))

    # 遍历第一个文件的startp列表
    for startp in startp_list1:
        x = []
        opfile1.seek(4 * (startp-500), 0)
        for num in range(0, wl):
            data = int.from_bytes(opfile1.read(4), "little", signed=False)
            x.append(data)
        arr_x1 = np.array(x)
        # 多项式拟合去除基线
        p = np.polyfit(np.arange(len(arr_x1)), arr_x1, deg=0)  # 常数拟合
        baseline_fit1 = np.polyval(p, np.arange(len(arr_x1)))
        arr_x1 = arr_x1 - baseline_fit1
        max_val1 = arr_x1[500]
        # max_val1 = np.max(arr_x1)
        if max_val1 != 0:  # 避免除以0
            arr_x1 = arr_x1 * (10000.0 / abs(max_val1))
        arr_t1 = 0.0002 * np.arange(wl)
        # 使用scatter绘制数据点，颜色为蓝色
        ax.scatter(arr_t1, arr_x1, color='red', alpha=0.01, s=1)

    # 遍历第二个文件的startp列表
    for startp in startp_list2:
        x = []
        opfile2.seek(4 * (startp-500), 0)
        for num in range(0, wl):
            data = int.from_bytes(opfile2.read(4), "little", signed=False)
            x.append(data)
        arr_x2 = np.array(x)
        p = np.polyfit(np.arange(len(arr_x2)), arr_x2, deg=0)  # 常数拟合
        baseline_fit2 = np.polyval(p, np.arange(len(arr_x2)))
        # max_val2 = arr_x2[500]
        # max_val2 = np.max(arr_x2[520:540])
        # max_val2 = np.average(arr_x2[520:540])
        max_val2 = np.average(arr_x2[485:495])
        arr_x2 = (arr_x2 - baseline_fit2) * (10000 / abs(max_val2-baseline_fit2))
        # if max_val2 != 0:  # 避免除以0
        #     arr_x2 = arr_x2 * (10000.0 / abs(max_val2))
        arr_t2 = 0.0002 * np.arange(wl)
        # 使用scatter绘制数据点，颜色为红色
        ax.scatter(arr_t2, arr_x2, color='blue', alpha=0.05, s=1)

    # 设置图形属性
    ax.set_xlabel('Time (second)', fontsize=15)
    ax.set_ylabel('Amplitude (ADC)', fontsize=15)
    ax.grid(True)

    # 显示图像
    plt.show()

    return

__read()
