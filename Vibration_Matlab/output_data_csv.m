% 导出Simulink仿真数据到CSV文件

input_name = 'simulate';   % 修改

% Extract timeseries from Simulink output
ts = out.(input_name);

% Get time and data from the timeseries
time = ts.Time;
value = ts.Data;
% Combine into two-column matrix
data = [time, value];

% 选择导出路径
[~, path] = uigetfile('*.csv', 'Select a data file to match export location');
if isequal(path, 0)
    disp('Export cancelled.');
    return;
end

% 自动根据变量名设置输出文件名
output_filename = fullfile(path, [input_name '.csv']);
writematrix(data, output_filename);

% 显示导出信息
fprintf('✅ Exported %s to: %s\n', input_name, output_filename);
