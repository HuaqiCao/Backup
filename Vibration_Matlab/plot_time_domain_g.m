%% ============================================================
% 批量读取多个 CSV（前4行为表头：time, voltage），
% 去除增益与灵敏度，转换为时域加速度（单位 g），
% 可选去直流成分、时间对齐为 0，并在同一图中绘制多条曲线。
%% ============================================================
% Multi-CSV → remove gain(100) & sensitivity(1.026 V/g) → time-domain accel (g)

%% 参数设置
gain = 100;               % 前端放大器增益
sens_g_per_V = 1.026;     % 传感器灵敏度 (g/V)
remove_dc = true;         % 是否去直流（减均值）
zero_time_start = true;   % 是否把每条曲线对齐到 t = 0

%% 选择多个 CSV 文件
[files, path] = uigetfile('*.csv', ...
    '选择一个或多个 CSV（前4行表头：time(s), voltage(V)）', ...
    'MultiSelect','on');
if isequal(files,0), error('已取消选择'); end
if ischar(files), files = {files}; end  % 若仅选一个，转为 cell

%% 开始绘图
figure('Name','Time-Domain Acceleration (g)');
hold on; grid on;
legNames = cell(1, numel(files));
maxDuration = 0;

for k = 1:numel(files)
    infile = fullfile(path, files{k});

    % 跳过前4行（表头）
    fid = fopen(infile,'r');
    for i = 1:4, fgetl(fid); end
    fclose(fid);

    % 读取数据
    opts = detectImportOptions(infile, 'NumHeaderLines', 4);
    M = readmatrix(infile, opts);

    % 检查列数
    if size(M,2) < 2
        warning('文件 %s 列数不足，跳过。', files{k});
        continue;
    end

    % 时间与电压
    t = M(:,1);     % 时间(s)
    v = M(:,2);     % 电压(V)，含增益

    % 排序防乱序
    [t, idx] = sort(t(:));
    v = v(idx);

    % 电压 → 加速度 (g)
    acc_g = v ./ (gain * sens_g_per_V);

    % 是否去直流
    if remove_dc
        acc_g = acc_g - mean(acc_g, 'omitnan');
    end

    % 是否令 t 起始对齐 0
    if zero_time_start
        t = t - t(1);
    end

    % 记录最长时间（用于统一 x 轴）
    if ~isempty(t)
        dur = t(end) - t(1);
        maxDuration = max(maxDuration, dur);
    end

    % 绘图
    plot(t, acc_g, 'LineWidth', 1.2);

    % 图例名称
    [~, name] = fileparts(files{k});
    legNames{k} = sprintf('%s (g)', name);
end

%% 图形修饰
xlabel('Time (s)');
ylabel('Acceleration (g)');
title('Time-Domain Acceleration (g)');
legend(legNames, 'Interpreter','none', 'Location','best');

% 若有多条曲线，x 轴设为最长长度
if maxDuration > 0
    xlim([0, maxDuration]);
end

hold off;
