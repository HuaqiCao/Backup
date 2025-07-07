function load_vibration_data()
    % 弹出文件选择对话框
    [filename, pathname] = uigetfile('*.csv', '选择CSV数据文件');
    if isequal(filename,0)
        error('用户取消选择');
    end
    filepath = fullfile(pathname, filename);

    % 读取CSV文件
    data = readtable(filepath, 'HeaderLines', 4);
    time = data{:,1};  
    voltage = data{:,2}; 

    % 创建timeseries对象
    vibration_date = timeseries(voltage, time, 'Name', 'VibrationData');
    
    % 写入基础工作区
    assignin('base', 'voltage', vibration_date);
    fprintf('已成功写入工作区变量 voltage\n');
    
    % 可选验证
    fprintf('时间序列长度：%d\n', length(vibration_date.Time));
    fprintf('时间范围：%.4f ~ %.4f\n', vibration_date.Time(1), vibration_date.Time(end));
    
end