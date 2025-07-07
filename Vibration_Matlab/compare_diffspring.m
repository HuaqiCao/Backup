function simulate_spring_responses()
    % 选择一个加速度输入 CSV 文件（振源）
    [file, path] = uigetfile('*.csv', '选择一个加速度CSV文件');
    if isequal(file, 0)
        disp('取消选择');
        return;
    end
    input_file = fullfile(path, file);
    opts = detectImportOptions(input_file, 'NumHeaderLines', 4);
    data = readmatrix(input_file, opts);

    time = data(:,1);        % 时间（秒）
    accel_input = data(:,2); % 加速度（g）
    accel_input = accel_input - mean(accel_input); % 去直流偏置

    dt = mean(diff(time));
    fs = 1 / dt;
    t = time;

    % 获取用户输入的 4 组 (k, c) 参数
    prompt = {'k1 (N/m):', 'c1 (Ns/m):', ...
              'k2 (N/m):', 'c2 (Ns/m):', ...
              'k3 (N/m):', 'c3 (Ns/m):', ...
              'k4 (N/m):', 'c4 (Ns/m):'};
    dlgtitle = '输入四组弹簧参数';
    dims = [1 35];
    definput = {'82.50','0.0992','55','0.0441','66.27','0.0441','99.40','0.0992'};
    answer = inputdlg(prompt, dlgtitle, dims, definput);
    if isempty(answer)
        disp('取消输入');
        return;
    end

    m = 1.025;
    sys = cell(1,4);
    responses = zeros(length(t), 4);
    for i = 1:4
        k = str2double(answer{2*i-1});
        c = str2double(answer{2*i});
        num = [0 c k];
        den = [m c k];
        sys{i} = tf(num, den);
        % 使用 lsim 模拟系统响应，输入为加速度（g），乘以 9.80665 得到 m/s²
        responses(:,i) = lsim(sys{i}, accel_input * 9.80665, t);
        % 写入输出 CSV（单位为 m/s²，列格式和输入一致）
        out_data = [t responses(:,i) / 9.80665];  % 转回 g
        out_filename = fullfile(path, sprintf('Output%d.csv', i));
        writematrix(out_data, out_filename);
    end

    % === PSD 分析参数 ===
    ref_resistance = 1;  % 参考电阻，单位欧姆
    nfft = 2^nextpow2(length(t)/8);
    window = hamming(nfft);
    overlap = round(0.5 * nfft);

    % 图像句柄
    figure_linear = figure('Name', 'PSD: g^2/Hz');
    figure_dBm = figure('Name', 'PSD: dBm/Hz');

    % === 首先绘制输入加速度的 PSD ===
    [pxx_input, f] = pwelch(accel_input, window, overlap, nfft, fs);
    % g^2/Hz
    figure(figure_linear);
    loglog(f, pxx_input, '--', 'Color', [0.4 0.4 0.4], 'LineWidth', 1.5); hold on;
    % dBm/Hz
    pxx_input_watt = pxx_input / ref_resistance;
    pxx_input_dBm = 10 * log10(pxx_input_watt / 1e-3);
    figure(figure_dBm);
    semilogx(f, pxx_input_dBm, '--', 'Color', [0.4 0.4 0.4], 'LineWidth', 1.5); hold on;

    % === 绘制输出加速度 PSD ===
    for i = 1:4
        accel = responses(:,i) / 9.80665; % 单位：g
        [pxx, f] = pwelch(accel, window, overlap, nfft, fs);
        % 图1: g^2/Hz
        figure(figure_linear);
        loglog(f, pxx, 'LineWidth', 1.2); hold on;
        % 图2: dBm/Hz
        pxx_watt = pxx / ref_resistance;
        pxx_dBm = 10 * log10(pxx_watt / 1e-3);
        figure(figure_dBm);
        semilogx(f, pxx_dBm, 'LineWidth', 1.2); hold on;
    end

    % 图像美化（线性图）
    figure(figure_linear);
    xlabel('频率 (Hz)');
    ylabel('PSD (g^2/Hz)');
    title('加速度功率谱密度 (线性坐标)');
    grid on;
    legend({'输入加速度（MXC）', '弹簧1', '弹簧2', '弹簧3', '弹簧4'}, 'Interpreter', 'none');

    % 图像美化（dBm图）
    figure(figure_dBm);
    xlabel('频率 (Hz)');
    ylabel('PSD (dBm/Hz)');
    title('等效功率谱密度 (dBm/Hz)');
    grid on;
    legend({'输入加速度（MXC）', '弹簧1', '弹簧2', '弹簧3', '弹簧4'}, 'Interpreter', 'none');
        % === PSD积分能量（频带能量分析） ===
    fprintf('\n--- PSD频带能量分析 [0 ~ 100 Hz] ---\n');
    idx_band = (f >= 0) & (f <= 100);
    energy_input = trapz(f(idx_band), pxx_input(idx_band));
    fprintf('输入能量：%.4e g^2\n', energy_input);

    for i = 1:4
        accel = responses(:,i) / 9.80665; % g
        [pxx, ~] = pwelch(accel, window, overlap, nfft, fs);
        energy_out = trapz(f(idx_band), pxx(idx_band));
        ratio = energy_out / energy_input;

        fprintf('弹簧 %d:\n', i);
        fprintf('   输出能量：%.4e g^2\n', energy_out);
        fprintf('   归一化能量比：%.4f\n', ratio);
    end
end