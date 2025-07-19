% calculates the sampling rate & saves a new CSV file with the sampling rate included in the filename.     

% === Select multiple CSV files ===
[fileNames, folderPath] = uigetfile('*.csv', 'Select CSV files', 'MultiSelect', 'on');

if isequal(fileNames, 0)
    disp('❌ Selection cancelled.');
    return;
end

% Ensure fileNames is a cell array
if ischar(fileNames)
    fileNames = {fileNames};
end

for i = 1:length(fileNames)
    fullPath = fullfile(folderPath, fileNames{i});

    % === Read data, skip first 4 header lines ===
    opts = detectImportOptions(fullPath);
    opts.DataLines = [5, Inf];
    data = readmatrix(fullPath, opts);

    % === Calculate sampling rate from time column ===
    time = data(:, 1);
    dt = mean(diff(time), 'omitnan');
    fs = 1 / dt;

    % === Print sampling rate ===
    fprintf('📁 File: %s\n', fileNames{i});
    fprintf('📊 Sampling rate: %.2f Hz\n', fs);

    % === Save new CSV with sampling rate in filename ===
    [~, name, ~] = fileparts(fileNames{i});
    newName = sprintf('%s_fs%.0fHz.csv', name, fs);
    newPath = fullfile(folderPath, newName);
    writematrix(data, newPath);

    fprintf('✅ Saved to: %s\n\n', newPath);
end
