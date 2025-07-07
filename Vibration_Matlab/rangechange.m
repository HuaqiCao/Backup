% Prompt user for start and end times (seconds)
t0 = input('Enter the start time in seconds: ');
tt = input('Enter the end time in seconds: ');

% Select multiple CSV files
[filenames, path] = uigetfile('*.csv', 'Select CSV files', 'MultiSelect', 'on');
if isequal(filenames, 0)
    return; % Exit if canceled
end
if ~iscell(filenames)
    filenames = {filenames};
end

% Create output folder inside the input files' folder if it doesn't exist
output_folder = fullfile(path, 'rangechange');
if ~exist(output_folder, 'dir')
    mkdir(output_folder);
end

% Loop over each file, extract data in specified time range, and save
for i = 1:length(filenames)
    filename = filenames{i};
    
    % Read a small sample to calculate sampling frequency
    fsdata = readmatrix(fullfile(path, filename), 'Range', '20:22');
    fs = round(1 / (fsdata(2,1) - fsdata(1,1)));
    
    % Calculate start and end rows based on time inputs
    start_row = round(fs * t0) + 1;
    end_row = round(fs * tt) + 5;
    
    % Read data in the specified range
    data = readmatrix(fullfile(path, filename), 'Range', sprintf('%d:%d', start_row, end_row));
    
    % Construct new filename with time range prefix
    [~, name, ext] = fileparts(filename);
    new_filename = sprintf('%ds_to_%ds_%s%s', t0, tt, name, ext);
    
    % Save extracted data to the output folder inside input path
    writematrix(data, fullfile(output_folder, new_filename));
end
