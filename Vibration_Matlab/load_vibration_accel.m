function load_vibration_data()
    % 常量设定
    sen = 1.026;            % 灵敏度 (V/g)
    default_gain = 10.003;  % 默认增益
    default_fs = 10000;     % 默认采样率

    % 选择文件
    [filename, pathname] = uigetfile('*.csv', 'Select CSV file');
    if isequal(filename, 0)
        error('File selection canceled');
    end

    % 构造完整路径
    filepath = fullfile(pathname, filename);

    % 读取数据 (跳过前4行)
    data = readmatrix(filepath);
    time = data(5:end, 1);       % 时间列
    voltage = data(5:end, 2);    % 电压列

    % 采样率推断
    try
        fs = round(1 / (time(10) - time(9)));
    catch
        fs = default_fs;
        match = regexp(filename, '(\d+)fs', 'match');
        if ~isempty(match)
            fs = str2double(match{1}(1:end-2));
        end
    end

    % 增益识别
    gain = default_gain;
    if contains(filename, "1gain")
        gain = 1;
    elseif contains(filename, "10gain")
        gain = 10.003;
    elseif contains(filename, "100gain")
        gain = 100.122;
    end

    % 电压 -> 加速度 (单位 g)
    acceleration = voltage / (gain * sen);

    % 创建 timeseries 对象
    vibration_data = timeseries(acceleration, time, 'Name', 'VibrationData');

    % 分配到 base 工作区
    assignin('base', 'MXC_accel', vibration_data);
    fprintf('变量 "MXC_accel" 已分配至工作区。\n');

    % 显示信息
    fprintf('样本数: %d\n', length(vibration_data.Time));
    fprintf('时间范围: %.4f ~ %.4f\n', ...
        vibration_data.Time(1), vibration_data.Time(end));

    % 保存为新的 CSV 文件
    out_data = [time, acceleration];
    [~, name, ~] = fileparts(filename);
    out_filename = fullfile(pathname, [name '_accel.csv']);
    writematrix(out_data, out_filename);
    fprintf('转换后的数据已保存至:\n%s\n', out_filename);
end
