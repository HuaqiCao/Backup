function qzs_interactive_gui()
    % 主窗口设置 (大尺寸，确保图表和滑块布局美观)
    fig = uifigure('Name', 'QZS 准零刚度隔振器实时分析系统', 'Position', [100, 100, 1200, 750]);
    
    %% ------------------ 初始化全局/共享变量 ------------------
    % 存储读取的外部数据
    v_in_data = []; t_data = []; fs_rate = 2000; v_ref_data = []; t_ref_data = [];
    
    % 固定物理参数
    a_target = 60; tau_p = 70; G = 75000; M = 2; g = 9.81; c = 20; Ze_mm = 3;
    
    % 五组对比试验的固定参数 (用于 Figure 2, 3, 4, 5)
    test_params = [
        0.500, 0.755, 2.143, 0.942, 0.501;
        0.471, 1.000, 1.054, 2.684, 0.179;
        0.800, 0.800, 1.987, 0.050, 0.010;  % 用合理数值替换原NaN
        0.500, 0.800, 1.987, 0.060, 0.015;
        0.200, 0.800, 2.192, 0.070, 0.020];

    %% ------------------ 搭建左侧交互控制面板 ------------------
    pnl = uipanel(fig, 'Title', '目标无量纲参数调节(实时触发)', 'Position', [20, 20, 280, 710], 'FontSize', 14, 'FontWeight', 'bold');
    
    % 滑块 1: delta_hat
    uilabel(pnl, 'Text', '预压缩量 delta_hat (δ̂):', 'Position', [10, 640, 200, 22], 'FontSize', 12);
    sld_delta = uislider(pnl, 'Limits', [0.1, 0.9], 'Value', 0.5, 'Position', [15, 620, 240, 3]);
    
    % 滑块 2: a_hat
    uilabel(pnl, 'Text', '结构参数 a_hat (â):', 'Position', [10, 550, 200, 22], 'FontSize', 12);
    sld_ahat = uislider(pnl, 'Limits', [0.4, 0.99], 'Value', 0.755, 'Position', [15, 530, 240, 3]);
    
    % 滑块 3: alpha
    uilabel(pnl, 'Text', '刚度比 alpha (α):', 'Position', [10, 460, 200, 22], 'FontSize', 12);
    sld_alpha = uislider(pnl, 'Limits', [0.1, 3.0], 'Value', 0.942, 'Position', [15, 440, 240, 3]);
    
    % 滑块 4: alpha1
    uilabel(pnl, 'Text', '刚度比 alpha1 (α₁):', 'Position', [10, 370, 200, 22], 'FontSize', 12);
    sld_alpha1 = uislider(pnl, 'Limits', [0.1, 2.0], 'Value', 0.501, 'Position', [15, 350, 240, 3]);
    
    % 滑块 5: gamma
    uilabel(pnl, 'Text', '几何比 gamma (γ):', 'Position', [10, 280, 200, 22], 'FontSize', 12);
    sld_gamma = uislider(pnl, 'Limits', [1.1, 3.5], 'Value', 2.143, 'Position', [15, 260, 240, 3]);

    % 文件载入按钮
    btn_csv1 = uibutton(pnl, 'Text', '📂 载入振动输入 CSV', 'Position', [20, 140, 240, 35], 'FontSize', 12, 'ButtonPushedFcn', @(~,~) load_csv1());
    btn_csv2 = uibutton(pnl, 'Text', '📂 载入参考曲线 CSV', 'Position', [20, 80, 240, 35], 'FontSize', 12, 'ButtonPushedFcn', @(~,~) load_csv2());
    lbl_status = uilabel(pnl, 'Text', '等待数据导入...', 'Position', [20, 30, 240, 22], 'FontColor', [0.5 0.5 0.5], 'HorizontalAlignment', 'center');

    % 绑定滑块事件：只要数值一变，立刻调用更新绘图主函数
    sld_delta.ValueChangedFcn  = @(~,~) update_plots();
    sld_ahat.ValueChangedFcn   = @(~,~) update_plots();
    sld_alpha.ValueChangedFcn  = @(~,~) update_plots();
    sld_alpha1.ValueChangedFcn = @(~,~) update_plots();
    sld_gamma.ValueChangedFcn  = @(~,~) update_plots();

    %% ------------------ 搭建右侧多图选项卡 (Tab) ------------------
    tab_gp = uitabgroup(fig, 'Position', [320, 20, 860, 710]);
    
    tab1 = uitab(tab_gp, 'Title', '图1: 双Y轴实时曲线');
    ax1 = uiaxes(tab1, 'Position', [40, 60, 760, 580]); grid(ax1, 'on');
    
    tab2 = uitab(tab_gp, 'Title', '图2: 刚度曲线对比');
    ax2 = uiaxes(tab2, 'Position', [40, 60, 760, 580]); grid(ax2, 'on');
    
    tab3 = uitab(tab_gp, 'Title', '图3&4: 位移传递率');
    ax3 = uiaxes(tab3, 'Position', [40, 60, 760, 580]); grid(ax3, 'on');
    % 创建图3内置的小放大窗
    ax3_inset = uiaxes(tab3, 'Position', [500, 320, 260, 220]); grid(ax3_inset, 'on');
    
    tab5 = uitab(tab_gp, 'Title', '图5: 时域响应对比');
    % 因为图5包含多张子图，使用Panel进行内部排版
    grid_layout = uigridlayout(tab5, [3, 2]);
    
    % 执行首次绘图初始化
    update_plots();

    %% ------------------ 核心计算与绘图函数 ------------------
    function update_plots()
        % 1. 获取当前滑动条的实时数值
        d_hat = sld_delta.Value;
        a_hat = sld_ahat.Value;
        al_target = sld_alpha.Value;
        al1_target = sld_alpha1.Value;
        ga_target = sld_gamma.Value;
        
        % 2. 物理基础计算
        h1_t = sqrt(a_target^2 * (1/a_hat^2 - 1));
        Ze_hat = Ze_mm / 1000 / sqrt(a_target^2 + h1_t^2);
        
        %% ======= 实时绘制 【图1: 双Y轴曲线】 =======
        y_hat = linspace(-3, 3, 500);
        K_hat_c1 = zeros(size(y_hat)); f_hat_curve1 = zeros(size(y_hat));
        rho_t = (1 - a_hat^2) / (ga_target - 1)^2;
        d_hat1 = 1 - sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho_t) + rho_t) + d_hat;
        d_hat2 = 1 - sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_t) + 4*rho_t) + d_hat;
        x_e_hat_t = sqrt(1 - a_hat^2) + sqrt(rho_t);
        
        for i = 1:length(y_hat)
            xi = x_e_hat_t + y_hat(i);
            P1=sqrt(1-a_hat^2)-xi; P2=1-2*sqrt(1-a_hat^2)*xi+xi^2; P3=1+d_hat;
            P4=sqrt(1-a_hat^2+rho_t+2*sqrt(1-a_hat^2)*sqrt(rho_t))-xi;
            P5=1+rho_t+2*sqrt(1-a_hat^2)*sqrt(rho_t)-2*sqrt(1-a_hat^2+rho_t+2*sqrt(1-a_hat^2)*sqrt(rho_t))*xi+xi^2;
            P6=sqrt(1+2*sqrt(1-a_hat^2)*sqrt(rho_t)+rho_t)+d_hat1;
            P7=sqrt(1-a_hat^2)+2*sqrt(rho_t)-xi;
            P8=1+4*sqrt(1-a_hat^2)*sqrt(rho_t)+4*rho_t-2*(sqrt(1-a_hat^2)+2*sqrt(rho_t))*xi+xi^2;
            P9=sqrt(1+4*sqrt(1-a_hat^2)*sqrt(rho_t)+4*rho_t)+d_hat2;
            
            dP2=-2*sqrt(1-a_hat^2)+2*xi; dP5=-2*sqrt(1-a_hat^2+rho_t+2*sqrt(1-a_hat^2)*sqrt(rho_t))+2*xi; dP8=-2*(sqrt(1-a_hat^2)+2*sqrt(rho_t))+2*xi;
            dN1=-2*al_target*(1-P3*P2.^(-0.5))*(-1)-al_target*P1*P2.^(-1.5)*P3*dP2;
            dN3=-2*al1_target*(1-P6*P5.^(-0.5))*(-1)-al1_target*P4*P5.^(-1.5)*P6*dP5;
            dN5=-2*al_target*(1-P9*P8.^(-0.5))*(-1)-al_target*P7*P8.^(-1.5)*P9*dP8;
            
            K_hat_c1(i) = 1 + dN1 + dN3 + dN5;
            f_hat_curve1(i) = xi - 2*al_target*P1*(sqrt(P2)-P3)/sqrt(P2) - 2*al1_target*P4*(sqrt(P5)-P6)/sqrt(P5) - 2*al_target*P7*(sqrt(P8)-P9)/sqrt(P8);
        end
        
        % 清除原图并绘制 UI-双Y轴
        cla(ax1);
        yyaxis(ax1, 'left');
        plot(ax1, y_hat, f_hat_curve1, 'Color', [0 0.447 0.741], 'LineWidth', 2);
        ax1.YLabel.String = 'Dimensionless Force \hat{f}';
        ax1.YLim = [-6, 6];
        
        yyaxis(ax1, 'right');
        plot(ax1, y_hat, K_hat_c1, '--', 'Color', [0.85 0.325 0.098], 'LineWidth', 2);
        ax1.YLabel.String = 'Dimensionless Stiffness \hat{K}';
        ax1.YLim = [0, 1.5];
        
        ax1.XLabel.String = 'Dimensionless Displacement \hat{y}';
        title(ax1, '实时恢复力与无量纲刚度曲线 (滑动调节)');
        
        %% ======= 实时绘制 【图2: 刚度曲线对比组】 =======
        cla(ax2); hold(ax2, 'on');
        colors_line = lines(6);
        % 绘制实时调节的这一组曲线
        plot(ax2, y_hat, K_hat_c1, 'Color', 'k', 'LineWidth', 3, 'DisplayName', 'Current Parameter');
        
        % 循环绘制原代码中的5组对比曲线
        for j = 1:size(test_params, 1)
            dt_h = test_params(j,1); ah_h = test_params(j,2); gm_h = test_params(j,3);
            al_h = test_params(j,4); al1_h = test_params(j,5);
            K_loop = zeros(size(y_hat));
            rho_h = (1 - ah_h^2) / (gm_h - 1)^2;
            dh1 = 1 - sqrt(1 + 2*sqrt(1-ah_h^2)*sqrt(rho_h) + rho_h) + dt_h;
            dh2 = 1 - sqrt(1 + 4*sqrt(1-ah_h^2)*sqrt(rho_h) + 4*rho_h) + dt_h;
            xe_h = sqrt(1 - ah_h^2) + sqrt(rho_h);
            
            for i = 1:length(y_hat)
                xi = xe_h + y_hat(i);
                P1=sqrt(1-ah_h^2)-xi; P2=1-2*sqrt(1-ah_h^2)*xi+xi^2; P3=1+dt_h;
                P4=sqrt(1-ah_h^2+rho_h+2*sqrt(1-ah_h^2)*sqrt(rho_h))-xi; P5=1+rho_h+2*sqrt(1-ah_h^2)*sqrt(rho_h)-2*sqrt(1-ah_h^2+rho_h+2*sqrt(1-ah_h^2)*sqrt(rho_h))*xi+xi^2; P6=sqrt(1+2*sqrt(1-ah_h^2)*sqrt(rho_h)+rho_h)+dh1;
                P7=sqrt(1-ah_h^2)+2*sqrt(rho_h)-xi; P8=1+4*sqrt(1-ah_h^2)*sqrt(rho_h)+4*rho_h-2*(sqrt(1-ah_h^2)+2*sqrt(rho_h))*xi+xi^2; P9=sqrt(1+4*sqrt(1-ah_h^2)*sqrt(rho_h)+4*rho_h)+dh2;
                dP2=-2*sqrt(1-ah_h^2)+2*xi; dP5=-2*sqrt(1-ah_h^2+rho_h+2*sqrt(1-ah_h^2)*sqrt(rho_h))+2*xi; dP8=-2*(sqrt(1-ah_h^2)+2*sqrt(rho_h))*xi+xi^2;
                dN1=-2*al_h*(1-P3*P2.^(-0.5))*(-1)-al_h*P1*P2.^(-1.5)*P3*dP2;
                dN3=-2*al1_h*(1-P6*P5.^(-0.5))*(-1)-al1_h*P4*P5.^(-1.5)*P6*dP5;
                dN5=-2*al_h*(1-P9*P8.^(-0.5))*(-1)-al_h*P7*P8.^(-1.5)*P9*dP8;
                K_loop(i) = 1 + dN1 + dN3 + dN5;
            end
            plot(ax2, y_hat, K_loop, '--', 'Color', colors_line(j,:), 'LineWidth', 1.5, 'DisplayName', sprintf('Group %d', j));
        end
        ax2.XLim = [-0.8, 0.8]; ax2.YLim = [0, 1.5];
        title(ax2, 'Stiffness Curves Comparison');
        legend(ax2, 'Location', 'best');
        
        %% ======= 实时绘制 【图3: 位移传递率与局部放大窗】 =======
        cla(ax3); hold(ax3, 'on'); cla(ax3_inset); hold(ax3_inset, 'on');
        f_ex = linspace(0.1, 10, 500); f0 = sqrt(384.3/M)/(2*pi); % 预设基准频率
        zeta = c * (f0*2*pi) / (2 * 384.3);
        
        % 提取泰勒级数五组预设 mu 数值
        mu1_vals = [0.1907, 0.1188, 0.00048, 0.3367, 0.2189];
        mu3_vals = [1.3836, 1.2344, 0.0017, 0.3876, 0.2104];
        
        for idx = 1:5
            Ta = zeros(size(f_ex));
            for j = 1:length(f_ex)
                Ta(j) = compute_transmissibility(mu1_vals(idx), mu3_vals(idx), f_ex(j)/f0, Ze_hat, zeta);
            end
            plot(ax3, f_ex, Ta, 'LineWidth', 1.5, 'Color', colors_line(idx,:), 'DisplayName', sprintf('Group %d', idx));
            plot(ax3_inset, f_ex, Ta, 'LineWidth', 1.2, 'Color', colors_line(idx,:));
        end
        ax3.XLim = [0, 10]; ax3.YLim = [0, 10]; title(ax3, 'Displacement Transmissibility');
        legend(ax3, 'Location', 'northeast');
        ax3_inset.XLim = [6, 10]; ax3_inset.YLim = [0, 0.25]; title(ax3_inset, 'Inset (6-10Hz)');

        %% ======= 动态绘制 【图5: 时域响应多子图面板】 =======
        % 清除面板里的老图，防止叠加错位
        delete(grid_layout.Children);
        
        % 绘制子图 1: 输入信号
        ax5_in = uiaxes(grid_layout); grid(ax5_in, 'on');
        if isempty(v_in_data)
            title(ax5_in, '暂无输入信号，请在左侧载入CSV数据');
        else
            time_show = min(2, t_data(end)); idx_s = t_data <= time_show;
            plot(ax5_in, t_data(idx_s), v_in_data(idx_s), 'Color', [0.5 0.5 0.5], 'LineWidth', 2);
            title(ax5_in, 'Input Signal (V)');
            
            % 循环计算并绘制5个输出子图
            for idx = 1:5
                ax_out = uiaxes(grid_layout); grid(ax_out, 'on');
                N = length(v_in_data); freq = (0:N-1) * fs_rate / N; n_pos = floor(N/2);
                Omega_range = freq(1:n_pos) / f0;
                Ta_curve = zeros(1, n_pos);
                for j = 1:n_pos
                    Ta_curve(j) = compute_transmissibility(mu1_vals(idx), mu3_vals(idx), Omega_range(j), Ze_hat, zeta);
                end
                H_full = zeros(N, 1); H_full(1:n_pos) = Ta_curve; H_full(N:-1:N-n_pos+2) = conj(Ta_curve(2:n_pos));
                v_out = real(ifft(fft(v_in_data) .* H_full));
                
                plot(ax_out, t_data(idx_s), v_out(idx_s), 'Color', colors_line(idx,:), 'LineWidth', 1.5);
                title(ax_out, sprintf('Output Group %d (V)', idx));
            end
        end
    end

    %% ------------------ 内部辅助计算与文件操作 ------------------
    function Ta = compute_transmissibility(mu1, mu3, Omega, Ze_hat, zeta)
        if Omega < 1e-6, Ta = 1; return; end
        a = (9/16) * mu3^2 * Ze_hat^4; b = 1.5 * mu3 * (mu1 - Omega^2) * Ze_hat^2;
        c_val = (mu1 - Omega^2)^2 + (2*zeta*Omega)^2; d = -Omega^4;
        roots_Z2 = roots([a, b, c_val, d]);
        Z2_candidates = roots_Z2(abs(imag(roots_Z2)) < 1e-6 & real(roots_Z2) > 0);
        if isempty(Z2_candidates)
            Z2 = (Omega^2 / sqrt((mu1 - Omega^2)^2 + (2*zeta*Omega)^2))^2;
        else
            Z2 = min(real(Z2_candidates));
        end
        Z_hat = sqrt(Z2);
        cos_phi = (0.75 * mu3 * Ze_hat^2 * Z_hat^3 + (mu1 - Omega^2)*Z_hat) / (Omega^2 * Ze_hat);
        Ta = sqrt((Z_hat * cos_phi + Ze_hat)^2 + (Z_hat * sqrt(1-min(1,max(-1,cos_phi))^2) + 2*zeta*Omega*Z_hat)^2) / Ze_hat;
    end

    function load_csv1()
        [file, path] = uigetfile('*.csv', '请选择振动输入CSV文件');
        if isequal(file, 0), return; end
        try
            raw_data = readmatrix(fullfile(path, file), 'NumHeaderLines', 3);
            t_data = raw_data(:, 1);
            v_in_data = raw_data(:, 2) / 100;
            v_in_data = v_in_data - mean(v_in_data); % 去除直流分量
            fs_rate = 1 / (t_data(2) - t_data(1));
            lbl_status.Text = '✅ 振动输入文件加载成功！';
            update_plots();
        catch
            lbl_status.Text = '❌ 文件读取失败，请检查格式';
        end
    end

    function load_csv2()
        [file, path] = uigetfile('*.csv', '请选择参考曲线CSV文件');
        if isequal(file, 0), return; end
        try
            raw_data = readmatrix(fullfile(path, file), 'NumHeaderLines', 3);
            t_ref_data = raw_data(:, 1);
            v_ref_data = raw_data(:, 2) / 100;
            v_ref_data = v_ref_data - mean(v_ref_data);
            lbl_status.Text = '✅ 参考曲线加载成功！';
            update_plots();
        catch
            lbl_status.Text = '❌ 参考文件读取失败';
        end
    end
end