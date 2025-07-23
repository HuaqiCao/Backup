% extracts signal and baseline data from a CSV file based on a threshold.  
 
% Select a CSV file
[filename, path] = uigetfile('*.csv', 'Select CSV file');
if isequal(filename, 0)
    return;
end

% Read the CSV file
data = readmatrix(fullfile(path, filename));
time = data(:,1);
volt = data(:,2);

% Set parameters
window_size = 1;             % seconds
fs = round(1 / (time(10) - time(9)));  % sampling rate
num_windows = ceil((time(end) - time(5)) / window_size);

% Initialize storage
signal_windows = {};
baseline_windows = {};
signal_times = {};
baseline_times = {};
sigamp = [];

% Split into time windows and classify
for i = 1:num_windows
    start_idx = (i - 1) * window_size * fs + 5;
    end_idx = min(start_idx + window_size * fs - 1, length(time));
    window = volt(start_idx:end_idx);
    wintime = time(start_idx:end_idx);
    
    if max(window) - min(window) >= 0.15  % threshold: 150 mV
        signal_windows{end+1} = window;
        signal_times{end+1} = wintime;
        sigamp(end+1) = max(window);
    else
        baseline_windows{end+1} = window;
        baseline_times{end+1} = wintime;
    end
end

% Compute baseline standard deviations
baseline_std = zeros(1, length(baseline_windows));
for i = 1:length(baseline_windows)
    baseline_std(i) = std(baseline_windows{i});
end
avg_baseline_std = mean(baseline_std);

% Display result
fprintf('Average baseline std: %.6f\n', avg_baseline_std);

% Prepare output directory
out_dir = fullfile(path, 'signal_rejection');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

% Write signal and baseline data
signal_data = [vertcat(signal_times{:}), vertcat(signal_windows{:})];
baseline_data = [vertcat(baseline_times{:}), vertcat(baseline_windows{:})];
writematrix(signal_data, fullfile(out_dir, ['signal_', filename]));
writematrix(baseline_data, fullfile(out_dir, ['baseline_', filename]));
