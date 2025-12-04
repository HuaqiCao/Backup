% extracts a specified time range from multiple CSV files
% saves the extracted data to a new folder named 'rangechange'. 
% Prompt user for start and end times (seconds)
% 从多个 CSV 文件中截取指定时间范围的数据
% 输入开始时间 t0、结束时间 tt，并将结果保存到输入路径下的 rangechange 文件夹中

% === 输入时间范围（单位：秒）===
t0 = input('Enter the start time in seconds: ');
tt = input('Enter the end time in seconds: ');

% === 选择多个 CSV 文件 ===
[filenames, path] = uigetfile('*.csv', 'Select CSV files', 'MultiSelect', 'on');
if isequal(filenames, 0)
    return;     % 若取消选择则退出
end
if ~iscell(filenames)
    filenames = {filenames};
end

% === 创建输出文件夹（在输入路径下）===
output_folder = fullfile(path, 'rangechange');
if ~exist(output_folder, 'dir')
    mkdir(output_folder);
end

% === 遍历每个文件 ===
for i = 1:length(filenames)
    filename = filenames{i};
    
    % 读取小段数据以计算采样率（根据第 20–22 行）
    fsdata = readmatrix(fullfile(path, filename), 'Range', '20:22');
    fs = round(1 / (fsdata(2,1) - fsdata(1,1)));   % 推算采样频率

    % === 根据输入时间换算成行号 ===
    start_row = round(fs * t0) + 1;   % 起始行
    end_row   = round(fs * tt) + 5;   % 结束行（+4 行表头）

    % === 按行范围读取数据 ===
    data = readmatrix(fullfile(path, filename), ...
                      'Range', sprintf('%d:%d', start_row, end_row));

    % === 创建新文件名：前缀为时间范围 ===
    [~, name, ext] = fileparts(filename);
    new_filename = sprintf('%ds_to_%ds_%s%s', t0, tt, name, ext);

    % === 保存至 rangechange 文件夹 ===
    writematrix(data, fullfile(output_folder, new_filename));
end

