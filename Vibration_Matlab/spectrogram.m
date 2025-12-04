% Select multiple CSV files
[filenames, path] = uigetfile('*.csv', 'Select CSV files', 'MultiSelect', 'on');
if isequal(filenames, 0)
    return; % Exit if user cancels
end
if ~iscell(filenames)
    filenames = {filenames}; % Convert single file to cell array
end

for i = 1:length(filenames)
    filename = filenames{i};
    [~, name, ~] = fileparts(filename);
    
    % Read data, skipping first 4 rows
    data = readmatrix(fullfile(path, filename));
    data = data(5:end, :);
    
    % Parameters for PSD calculation
    sen = 1.026;      % Sensitivity (V/g)
    g = 9.81;         % Gravity (m/s^2)
    wint = 1;         % Window length (s)
    gain = 100.003;    % Default gain
    fs = 10000;       % Sampling frequency (Hz)
    
    % Adjust gain based on filename
    if contains(filename, "1gain")
        gain = 1;
    elseif contains(filename, "10gain")
        gain = 10.003;
    elseif contains(filename, "100gain")
        gain = 100.122;
    end
    
    % Extract sampling frequency from filename if available
    match = regexp(filename, '(\d+)fs', 'match');
    if ~isempty(match)
        fs_str = match{1}(1:end-2); % Remove "fs"
        fs = str2double(fs_str);
    end
    
    % Normalize voltage data to acceleration (g)
    data(:,2) = data(:,2) / (gain * sen);
    
    % Number of slices per second for spectrogram
    nSlices = 1 / wint;
    
    % Calculate spectrogram (user-defined function)
    [x_3D, y_3D, z_3D] = Mide_Spectrogram(data, fs, nSlices);
    
    % Plot 3D spectrogram in log scale
    figure;
    surf(x_3D, y_3D, log10(z_3D), 'EdgeColor', 'none');
    set(gca, 'YScale', 'log');
    set(gca, 'ZScale', 'log');
    xlim([wint 200]);
    ylim([1/wint fs/2]);
    xlabel('Time (s)');
    ylabel('Frequency (Hz)');
    zlabel('Amplitude');
    title(name, 'Interpreter', 'none');
    grid on;
    colormap(jet);
    colorbar;
    view(2);
end
