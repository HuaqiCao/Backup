% ============================================================
% 从 CSV 文件读取振动电压数据 → 创建 timeseries → 放入工作区
% ============================================================

function load_vibration_voltage()
    % === 设置输出变量名 ===
    var_name = 'Vibration_Data';

    % === 选择 CSV 文件 ===
    [filename, pathname] = uigetfile('*.csv', '选择CSV数据文件');
    if isequal(filename,0)
        error('用户取消选择');
    end
    filepath = fullfile(pathname, filename);

    % === 读取 CSV（跳过前 4 行头信息）===
    data = readtable(filepath, 'HeaderLines', 4);
    time = data{:,1};      % 时间列
    voltage = data{:,2};   % 电压列

    % === 推断采样频率 ===
    dt = mean(diff(time));   % 平均采样间隔
    fs = 1/dt;               % 采样频率 Hz
    fprintf('采样频率约 %.2f Hz\n', fs);

    % === 创建 timeseries 对象（以原始时间为基准）===
    ts = timeseries(voltage, time, 'Name', var_name);

    % === 强制统一采样点为等间隔 ===
    ts = resample(ts, time(1):dt:time(end));

    % === 写入 MATLAB 基础工作区 ===
    assignin('base', var_name, ts);
    fprintf('✅ 已成功写入工作区变量 %s\n', var_name);
    
    % === 打印基本信息 ===
    fprintf('📏 时间序列长度：%d\n', length(ts.Time));
    fprintf('⏱️ 时间范围：%.4f ~ %.4f\n', ts.Time(1), ts.Time(end));
end
