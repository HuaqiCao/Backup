
% 已知参数
M = 12.6;                % 载荷质量 (kg)
g = 9.81;                % 重力加速度 (m/s^2)

% 材料属性 (黄铜)
G = 77e9;                % 剪切模量 (Pa)
rho = 7930;              % 密度 (kg/m^3)
sigma_b = 505e6;         % 抗拉屈服强度 (Pa)

% 固有频率目标
f0_vertical = 1.3;                 
k_target = M * (2 * pi * f0_vertical)^2;

% 搜索范围
d_wire_range = 1e-3:1e-3:5e-3;
d_in_range = 5e-3:1e-3:9.5e-2;
d_hook_range = 1e-3:1e-3:5e-3;
r_hook_range = 2e-3:1e-3:8e-3;

zeta = 0.02;

results = [];
best_peak = Inf;
best_H = [];
best_params = [];

for i = 1:length(d_wire_range)
    for j = 1:length(d_in_range)
        for m = 1:length(d_hook_range)
            for n = 1:length(r_hook_range)

                d_wire = d_wire_range(i);
                d_in   = d_in_range(j);
                d_hook = d_hook_range(m);
                r_hook = r_hook_range(n);

                d_out = d_in + 2 * d_wire;
                D = (d_in + d_out) / 2;
                c_index = D / d_wire;
                if d_out > 0.1
                    continue;
                end

                n_calc = (G * d_wire^4) / (8 * D^3 * k_target);
                n_eff_options = unique(round([n_calc+1.5, n_calc+2, n_calc+2.2]));

                for k = 1:length(n_eff_options)
                    n_eff = n_eff_options(k);
                    n_total = n_eff + 2;

                    k_actual = (G * d_wire^4) / (8 * D^3 * n_eff);

                    A_coil = pi * (d_wire^2 / 4);
                    L_wire = n_eff * pi * D;
                    m_s = rho * A_coil * L_wire;
                    m_eq = M + (1/3) * m_s;

                    delta_static = m_eq * g / k_actual;
                    L_eq = n_total * d_wire + delta_static + 2 * d_hook + 2 * r_hook;

                    if L_eq > 0.33
                        continue;
                    end

                    f0_radial = sqrt(g / L_eq) / (2 * pi);
                    F_max = m_eq * g;
                    Kw = (4*c_index - 1)/(4*c_index - 4) + 0.615/c_index;
                    tau_e = Kw * (8 * F_max * D) / (pi * d_wire^3);
                    FOS_e = sigma_b / tau_e;
                    if FOS_e < 1/0.45
                        continue;
                    end

                    kappa_3 = (4 * c_index^2 - c_index - 1) / (4 * c_index * (c_index - 1));
                    kappa_3_prime = kappa_3 + 1 / (4 * c_index);
                    sigma_max = kappa_3_prime * (16 * D * F_max) / (pi * d_wire^3);
                    if sigma_max >= 0.7 * sigma_b
                        continue;
                    end

                    f_plot = linspace(0.01, 100, 1000);
                    omega = 2 * pi * f_plot;
                    wn = sqrt(k_actual / m_eq);
                    H = 1 ./ sqrt((1 - (omega / wn).^2).^2 + (2 * zeta * omega / wn).^2);
                    H_peak = max(H);

                    if H_peak < best_peak
                        best_peak = H_peak;
                        best_H = H;
                        best_params = [d_wire, D, n_total, n_eff, m_s, m_eq, k_actual, ...
                            sqrt(k_actual/m_eq)/(2*pi), FOS_e, f0_radial, sigma_max];
                    end

                    results = [results;
                        d_wire*1000, d_in*1000, d_out*1000, D*1000, ...
                        c_index, n_total, n_eff, d_wire*1000, ...
                        n_total*d_wire*1000, L_eq*1000, A_coil*1e6, ...
                        m_s, m_eq, k_actual, ...
                        sqrt(k_actual/m_eq)/(2*pi), ...
                        tau_e/1e6, FOS_e, f0_radial, sigma_max/1e6];
                end
            end
        end
    end
end

if ~isempty(results)
    header = {'线径_d_mm', '内径_din_mm', '外径_dout_mm', '中径_D_mm', '旋绕比_c', ...
    '总圈数_n_total', '有效圈数_n_eff', '节距_p_mm', '自由长度_L0_mm', ...
    '装配长度_Leq_mm', '横截面积_A_mm2', '弹簧质量_ms_kg', ...
    '等效质量_meq_kg', '刚度_k_N_m', '轴向固频_fn_Hz', ...
    '最大剪应力_tau_MPa', '疲劳安全系数_FOSf', '径向固频_fr_Hz', ...
    '最大拉应力_sigma_MPa'};

    result_table = array2table(results, 'VariableNames', header);

    disp('满足设计约束的弹簧参数:');
    disp(result_table);

    figure;
    semilogy(f_plot, best_H, 'r-', 'LineWidth', 2);
    xlabel('频率 (Hz)');
    ylabel('频响 |H(\omega)|');
    title('频率响应曲线');
    grid on;
    set(gca, 'YScale', 'log');
    ylim([1e-3, 1e2]);

    fprintf('\n=== 最佳弹簧参数 ===\n');
    fprintf('线径: %.1f mm\n', best_params(1)*1000);
    fprintf('中径: %.1f mm\n', best_params(2)*1000);
    fprintf('总圈数: %d (有效圈数: %d)\n', best_params(3), best_params(4));
    fprintf('弹簧质量: %.3f kg\n', best_params(5));
    fprintf('等效质量: %.3f kg\n', best_params(6));
    fprintf('刚度: %.1f N/m\n', best_params(7));
    fprintf('轴向固有频率: %.2f Hz\n', best_params(8));
    fprintf('疲劳安全系数: %.2f\n', best_params(9));
    fprintf('径向固有频率: %.2f Hz\n', best_params(10));
    fprintf('最大拉应力: %.2f MPa\n', best_params(11)/1e6);
else
    disp('未找到满足所有约束的解。');
end
