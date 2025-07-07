clear;

% Select CSV files
[filenames, path] = uigetfile('*.csv', 'Select CSV files', 'MultiSelect', 'on');
if isequal(filenames, 0)
    return;
end

% Ensure filenames is a cell array
if ~iscell(filenames)
    filenames = {filenames};
end

% Create output folder if it doesn't exist
if ~exist('fschange', 'dir')
    mkdir('fschange');
end

% Process each file
for i = 1:length(filenames)
    filename = filenames{i};
    data = readmatrix(fullfile(path, filename));

    % Estimate original sampling rate
    fs_orig = round(1 / (data(101,1) - data(100,1)));

    % Target sampling rate: half of original
    fs_target = floor(fs_orig / 2);
    if fs_target >= fs_orig
        warning('Target rate >= original rate. Skipping %s.', filename);
        continue;
    end

    % Create new filename
    [~, name, ext] = fileparts(filename);
    fs_str = sprintf('%.0E', fs_target);
    new_filename = sprintf('%sHzfs_%s%s', fs_str, name, ext);

    % Keep header (first 4 rows)
    new_data = data(1:4, :);

    % Resample the rest of the data
    new_data = [new_data; resample(data(5:end, :), fs_target, fs_orig)];

    % Write to new file
    writematrix(new_data, fullfile('fschange', new_filename));
end


