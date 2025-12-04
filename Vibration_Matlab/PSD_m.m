% Get the filenames and path of the selected CSV files
% 1）选择多个 CSV 文件并读取（跳过前4行）
% 2）根据文件名自动识别 gain、fs
% 3）电压 → 加速度(g)
% 4）使用自定义 Hanning 窗 + 重叠 + FFT 计算 PSD
% 5）绘制 LPSD（g/√Hz），并自动生成 legend

% === 选择 CSV 文件 ===
[filenames, path] = uigetfile('*.csv', 'Select CSV files', 'MultiSelect', 'on');

% 如果取消选择，直接退出
if isequal(filenames,0)
   return;
end

% 转成 cell 数组格式
if ~iscell(filenames)
    filenames = {filenames};
end

% 图例容器
legends = cell(1,length(filenames)); 

% === 遍历每个文件 ===
for i = 1:length(filenames)

    filename = filenames{i};
    data = readmatrix(fullfile(path, filename));

    % 跳过前4行，取第2列数据（电压）
    data = data(5:end, :); 
    data = data(:,2);

    % 参数设定
    sen = 1.000;        % 灵敏度 V/g
    g = 9.81;           % m/s^2（此程序中未直接使用）
    wint = 5;           % 每窗口时长 5s
    gain = 100.003;     % 默认增益
    fs = 10000;         % 默认采样率

    % === 从文件名判断 gain ===
    if contains(filename,"1gain")
        gain = 1;
    elseif contains(filename,"10gain")
        gain = 10.003;
    elseif contains(filename,"100gain")
        gain = 100.122;
    end

    % === 从文件名识别采样率，例如：“10000fs” ===
    match = regexp(filename, '(\d+)fs', 'match');
    if ~isempty(match)
        fs_str = match{1}(1:end-2);
        fs = str2double(fs_str);
    end

    % === 窗口大小 & FFT 参数 ===
    window_size = wint*fs;
    nfft = 2^nextpow2(window_size);
    overlap = nfft/2;
    f = (0:nfft/2-1)*fs/nfft;

    % === 电压 → g ===
    data = data / (gain * sen);

    % Hanning 窗（能量归一化）
    window = hann(window_size);
    window = window./sqrt(mean(window.^2));

    % 分帧 + 加窗
    data_windowed = buffer(data, window_size, overlap, 'nodelay');
    data_windowed = data_windowed .* window;

    % === PSD 计算 ===
    psd = zeros(nfft/2, size(data_windowed, 2));
    for j = 1:size(data_windowed, 2)
        fft_data = fft(data_windowed(:,j), nfft);
        psd(:,j) = abs(fft_data(1:nfft/2)).^2 / (fs*nfft);
        psd(2:end-1,j) = 2*psd(2:end-1,j);  % 单边谱
    end
    psd = mean(psd, 2);

    % === 绘制 LPSD（g/√Hz）===
    loglog(f, sqrt(psd));
    hold on;

    % 图例名称
    [~, name, ~] = fileparts(filename);
    legends{i} = name;

end

% === 设置图例 ===
legend(legends,'FontSize',18,'Location','northeast','Interpreter','none');

xlabel("$Frequency (Hz)$","Interpreter","latex");
ylabel("$PSD\left[g/\sqrt{Hz}\right]$","Interpreter","latex");
grid on;
title("Power Spectrum Density");

hold off;
