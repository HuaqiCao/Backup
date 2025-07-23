% loads vibration voltage data from a CSV file
% converts it to a timeseries object in the workspace.

function load_vibration_voltage()
    % 设置变量名
    var_name = 'Vibration_Data';

    % 弹出文件选择对话框
    [filename, pathname] = uigetfile('*.csv', '选择CSV数据文件');
    if isequal(filename,0)
        error('用户取消选择');
    end
    filepath = fullfile(pathname, filename);

    % 读取CSV文件（跳过前4行）
    data = readtable(filepath, 'HeaderLines', 4);
    time = data{:,1};  
    voltage = data{:,2}; 

    % 创建timeseries对象
    ts = timeseries(voltage, time, 'Name', var_name);

    % 写入基础工作区
    assignin('base', var_name, ts);
    fprintf('✅ 已成功写入工作区变量 %s\n', var_name);
    
    % 可选验证
    fprintf('📏 时间序列长度：%d\n', length(ts.Time));
    fprintf('⏱️ 时间范围：%.4f ~ %.4f\n', ts.Time(1), ts.Time(end));
end
