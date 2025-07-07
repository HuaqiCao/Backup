% Extract timeseries from Simulink output
ts = out.Crystal_accel2;

% Get time and data from the timeseries
time = ts.Time;
value = ts.Data;

% Combine into two-column matrix
data = [time, value];

% 或者用 uigetfile 选一个文件并提取路径：
[~, path] = uigetfile('*.csv', 'Select a data file to match export location');

if isequal(path, 0)
    disp('Export cancelled.');
    return;
end

% Export to CSV in the same folder as the selected data file
output_filename = fullfile(path, 'Crystal_accel2.csv');
writematrix(data, output_filename);

% Display confirmation
fprintf('Exported to: %s\n', output_filename);

