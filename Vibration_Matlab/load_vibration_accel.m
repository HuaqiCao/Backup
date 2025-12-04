%% ============================================================
% 1）从 CSV 文件读取振动电压信号；
% 2）根据增益与灵敏度换算为加速度（g 或 m/s^2）；
% 3）创建 timeseries 对象写入工作区；
% 4）将加速度结果另存为新的 CSV 文件。
%% ============================================================

function load_vibration_accel()

    % ====== 常量设定 ======
    sen = 1.026;              % 传感器灵敏度 (V/g)
    default_gain = 100.003;   % 默认放大倍数
    default_fs = 100000;      % 默认采样率
    g_const = 9.80665;        % g → m/s^2 换算系数
    to_SI_unit = true;        % 是否转换为 m/s^2 输出

    % ====== 输出变量名 ======
    output_var_name = 'Vibration_Data';

    % ====== 选择 CSV 文件 ======
    [filename, pathname] = uigetfile('*.csv', 'Select CSV file');
    if isequal(filename, 0)
        error('❌ 文件选择已取消');
    end
    filepath = fullfile(pathname, filename);

    % ====== 读取 CSV（跳过前 4 行头）======
    data = readmatrix(filepath, 'NumHeaderLines', 4);
    time = data(:, 1);        % 时间轴 (s)
    voltage = data(:, 2);     % 电压值 (V)

    % ====== 根据时间步长自动推断采样率 ======
    try
        dt = mean(diff(time));
        fs = round(1 / dt);
    catch
        fs = default_fs;
        match = regexp(filename, '(\d+)fs', 'match');
        if ~isempty(match)
            fs = str2double(match{1}(1:end-2));
        end
    end

    % ====== 根据文件名自动识别增益 ======
    gain = default_gain;
    if contains(filename, "1gain")
        gain = 1;
    elseif contains(filename, "10gain")
        gain = 10.003;
    elseif contains(filename, "100gain")
        gain = 100.122;
    end

    % ====== 电压转换为加速度（单位 g）======
    acceleration_g = voltage / (gain * sen);

    % ====== 根据设置转换为 m/s² 或 g ======
    if to_SI_unit
        acceleration = acceleration_g * g_const;   % g → m/s²
        unit_str = 'm/s^2';
        suffix = '_accel_ms2.csv';
    else
        acceleration = acceleration_g;
        unit_str = 'g';
        suffix = '_accel_g.csv';
    end

    % ====== 创建 timeseries 对象，并加载到工作区 ======
    ts = timeseries(acceleration, time, 'Name', output_var_name);
    assignin('base', output_var_name, ts);

    % ====== 输出基础信息 ======
    fprintf('变量 "%s" 已加载到工作区\n', output_var_name);
    fprintf('采样率: %d Hz\n', fs);
    fprintf('样本数: %d\n', length(time));
    fprintf('时间范围: %.4f ~ %.4f 秒\n', time(1), time(end));
    fprintf('单位: %s\n', unit_str);

    % ====== 保存加速度结果为新的 CSV 文件 ======
    out_data = [time, acceleration];
    [~, name, ~] = fileparts(filename);
    out_filename = fullfile(pathname, [name suffix]);
    writematrix(out_data, out_filename);

    fprintf('✅ 加速度数据已保存至:\n%s\n', out_filename);
end
