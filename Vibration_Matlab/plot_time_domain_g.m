% Multi-CSV → remove gain(100) & sensitivity(1.026 V/g) → time-domain accel (g)

%% 参数
gain = 100;               % 前端增益
sens_g_per_V = 1.026;     % 传感器灵敏度 (g/V)
remove_dc = true;         % 是否去直流（减去均值）
zero_time_start = true;   % 是否把每条曲线的起点对齐到 t=0

%% 选择文件（可多选）
[files, path] = uigetfile('*.csv', ...
    '选择一个或多个 CSV（前4行表头：time(s), voltage(V)）', ...
    'MultiSelect','on');
if isequal(files,0), error('已取消选择'); end
if ischar(files), files = {files}; end  

%% 绘图
figure('Name','Time-Domain Acceleration (g)');
hold on; grid on;
legNames = cell(1, numel(files));
maxDuration = 0;

for k = 1:numel(files)
    infile = fullfile(path, files{k});

    % 跳过前4行表头
    fid = fopen(infile,'r');
    for i = 1:4, fgetl(fid); end
    fclose(fid);

    % 读取数据
    opts = detectImportOptions(infile, 'NumHeaderLines', 4);
    M = readmatrix(infile, opts);
    if size(M,2) < 2
        warning('文件 %s 列数不足，跳过。', files{k}); 
        continue;
    end
    t = M(:,1);                   % 时间 (s)
    v = M(:,2);                   % 电压 (V, 含增益)

    % 清洗/排序
    [t, idx] = sort(t(:));
    v = v(idx);

    % 电压 -> 加速度 (g)
    acc_g = v ./ (gain * sens_g_per_V);

    if remove_dc
        acc_g = acc_g - mean(acc_g, 'omitnan');
    end
    if zero_time_start
        t = t - t(1);
    end

    % 记录该条持续时长，以设定统一 x 轴上限
    if ~isempty(t)
        dur = t(end) - t(1);
        maxDuration = max(maxDuration, dur);
    end

    % 画图
    plot(t, acc_g, 'LineWidth', 1.2);
    [~, name] = fileparts(files{k});
    legNames{k} = sprintf('%s (g)', name);
end

xlabel('Time (s)');
ylabel('Acceleration (g)');
title('Time-Domain Acceleration (g)');
legend(legNames, 'Interpreter','none', 'Location','best');

% 横轴最大为“数据的长度”（取所有文件中最长的一条）
if maxDuration > 0
    xlim([0, maxDuration]);
end

hold off;
