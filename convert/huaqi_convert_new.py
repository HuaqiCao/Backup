import time
import os
import struct 
import numpy as np
from nptdms import TdmsFile

def process_tdms_files(input_path, output_path, sample_rate=5000.0, full_scale=20.0):
    files = [f for f in os.listdir(input_path) if f.endswith(".tdms") and "04-2" in f]

    for file in files:
        fname = os.path.join(input_path, file)
        
        if os.path.getsize(fname) < 2 * 1024 * 1024 * 1024:
            continue

        print(f"Processing file: {fname}")
        start = time.process_time()
        tdms_file = TdmsFile.read(fname)
        end = time.process_time()
        print(f'Time to read the file: {end - start:.2f} seconds')

        all_groups = tdms_file.groups()
        if not all_groups:
            print("No group found in TDMS file.")
            continue

        if len(all_groups) > 1:
            print("Original TDMS file from NI.")
            group = all_groups[1]
        else:
            print("Converted TDMS file.")
            group = all_groups[0]

        group_name = group.name
        all_group_channels = group.channels()

        if not all_group_channels:
            print(f"No channels found in group '{group_name}', skipping file.")
            continue

        group_output_dir = os.path.join(output_path, group_name)
        os.makedirs(group_output_dir, exist_ok=True)

        for channel in all_group_channels:
            channel_name = channel.name
            data = channel[:]

            channel_folder = os.path.join(group_output_dir, channel_name)
            os.makedirs(channel_folder, exist_ok=True)

            output_file_path = os.path.join(channel_folder, f"{channel_name}.bin")
            trans(output_file_path, data, sample_rate, full_scale)

def trans(binfile, bindata, sample_rate, full_scale):
    print(f"Creating file: {binfile}")
    with open(binfile, 'wb') as fileBIN2:
        # 写入自定义头部
        fileBIN2.write(struct.pack('<I', 0x00006C20))
        fileBIN2.write(struct.pack('<f', sample_rate))
        fileBIN2.write(struct.pack('<f', full_scale))

        tot_num = len(bindata) // 20000

        # 模拟 24-bit 有符号数据（范围：-2^23 ~ 2^23 - 1）
        adc_min = -2**23
        adc_max = 2**23 - 1
        scale_range = adc_max - adc_min

        for num in range(tot_num):
            if num % 100 == 0:
                print(f"Processing chunk {100 * num / tot_num:.2f}%")

            chunk = bindata[20000 * num:20000 * (num + 1)]

            # 假设数据是 int32 且真实只有 24bit 有效（需要截断/缩放）
            # 将其归一化到 [0, 2^32 - 1]
            normalized = ((chunk.astype(np.int64) - adc_min) * (2**32 - 1) / scale_range).astype('<u4')

            fileBIN2.write(normalized.tobytes())

    print(f"Finished processing file: {binfile}")


