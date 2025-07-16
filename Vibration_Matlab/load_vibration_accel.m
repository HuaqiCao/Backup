function load_vibration_data()
    % ====== 常量设定 ======
    sen = 1.026;             % 灵敏度 (V/g)
    default_gain = 10.003;   % 默认增益
    default_fs = 10000;      % 默认采样率
    g_const = 9.80665;       % 重力加速度 (m/s^2 per g)
    to_SI_unit = true;       % 是否转为 m/s^2

    % ====== 🚀 改动变量名 ======
    output_var_name = 'Vibration_Data';

    % ====== 选择 CSV 文件 ======
    [filename, pathname] = uigetfile('*.csv', 'Select CSV file');
    if isequal(filename, 0)
        error('❌ 文件选择已取消');
    end
    filepath = fullfile(pathname, filename);

    % ====== 读取数据（跳过前4行）======
    data = readmatrix(filepath, 'NumHeaderLines', 4);
    time = data(:, 1);         % 时间（秒）
    voltage = data(:, 2);      % 电压（伏特）

    % ====== 采样率推断 ======
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

    % ====== 增益识别 ======
    gain = default_gain;
    if contains(filename, "1gain")
        gain = 1;
    elseif contains(filename, "10gain")
        gain = 10.003;
    elseif contains(filename, "100gain")
        gain = 100.122;
    end

    % ====== 电压 → 加速度（单位 g）======
    acceleration_g = voltage / (gain * sen);  % 单位 g

    % ====== 是否转换为 m/s^2 ======
    if to_SI_unit
        acceleration = acceleration_g * g_const;
        unit_str = 'm/s^2';
        suffix = '_accel_ms2.csv';
    else
        acceleration = acceleration_g;
        unit_str = 'g';
        suffix = '_accel_g.csv';
    end

    % ====== 创建 timeseries 对象 ======
    ts = timeseries(acceleration, time, 'Name', output_var_name);
    assignin('base', output_var_name, ts);

    % ====== 输出信息 ======
    fprintf('✅ 变量 "%s" 已加载到工作区\n', output_var_name);
    fprintf('采样率: %d Hz\n', fs);
    fprintf('样本数: %d\n', length(time));
    fprintf('时间范围: %.4f ~ %.4f 秒\n', time(1), time(end));
    fprintf('单位: %s\n', unit_str);

    % ====== 保存结果到 CSV ======
    out_data = [time, acceleration];
    [~, name, ~] = fileparts(filename);
    out_filename = fullfile(pathname, [name suffix]);
    writematrix(out_data, out_filename);
    fprintf('✅ 加速度数据已保存至:\n%s\n', out_filename);
end
