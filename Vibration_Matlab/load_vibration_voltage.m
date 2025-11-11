function load_vibration_voltage()
    % 设置变量名
    var_name = 'b';

    % 选择 CSV 文件
    [filename, pathname] = uigetfile('*.csv', '选择CSV数据文件');
    if isequal(filename,0)
        error('用户取消选择');
    end
    filepath = fullfile(pathname, filename);

    % 读取 CSV（跳过前4行）
    data = readtable(filepath, 'HeaderLines', 4);
    time = data{:,1};
    voltage = data{:,2};

    % 检查采样是否等间隔并计算采样周期
    dt = mean(diff(time));        % 平均采样时间
    fs = 1/dt;                    % 采样频率 (Hz)
    fprintf('采样频率约 %.2f Hz\n', fs);

    % 创建 timeseries 对象（带固定采样间隔）
    ts = timeseries(voltage, time, 'Name', var_name);
    ts = resample(ts, time(1):dt:time(end));  % 统一为等间隔时间

    % 写入基础工作区
    assignin('base', var_name, ts);
    fprintf('✅ 已成功写入工作区变量 %s\n', var_name);
    
    % 可选验证
    fprintf('📏 时间序列长度：%d\n', length(ts.Time));
    fprintf('⏱️ 时间范围：%.4f ~ %.4f\n', ts.Time(1), ts.Time(end));
end
