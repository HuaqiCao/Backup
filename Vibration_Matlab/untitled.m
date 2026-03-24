clear; clc;

%% 目标无量纲参数（取自原文Figure 7）
delta_hat_target = 0.5;      % δ̂ = δ / sqrt(a^2 + h1^2)
a_hat_target     = 0.755;    % â = a / sqrt(a^2 + h1^2)
alpha_target     = 0.942;    % α = k1/k2
alpha1_target    = 0.501;    % α₁ = k3/k2
gamma_target     = 2.143;    % γ = h/d

fprintf('目标无量纲参数:\n');
fprintf('  δ̂ = %.3f, â = %.3f, α = %.3f, α₁ = %.3f, γ = %.3f\n\n', ...
    delta_hat_target, a_hat_target, alpha_target, alpha1_target, gamma_target);

%% 定义物理参数遍历范围
k1_range = 100:200:900;      % 上斜弹簧刚度 N/m
h_range  = 0.10:0.05:0.30;   % 中间斜弹簧高度 m
h1_range = 0.14:0.05:0.40;   % 上斜弹簧高度 m

fprintf('遍历范围：\n');
fprintf('  k1: %.0f ~ %.0f N/m, 步长 %.0f N/m\n', min(k1_range), max(k1_range), k1_range(2)-k1_range(1));
fprintf('  h: %.2f ~ %.2f m, 步长 %.2f m\n', min(h_range), max(h_range), h_range(2)-h_range(1));
fprintf('  h1: %.2f ~ %.2f m, 步长 %.2f m\n', min(h1_range), max(h1_range), h1_range(2)-h1_range(1));
fprintf('总组合数: %d\n\n', length(k1_range) * length(h_range) * length(h1_range));

fprintf('遍历结果（物理量已转换为 mm）:\n');
fprintf('========================================================================================================================================================\n');
fprintf(' k1(N/m) | h(mm) | h1(mm) | k2(N/m) | k3(N/m) | a(mm) | d(mm) | delta(mm) | ρ | â实际 | â误差 %% | γ实际 | γ误差 %% | α实际 | α₁实际 | δ̂实际 | δ̂误差 %%\n');
fprintf('--------------------------------------------------------------------------------------------------------------------------------------------------------\n');

% 创建图形窗口
figure('Position', [100, 100, 1200, 600]);

% 用不同颜色区分不同的k1值
colors = lines(length(k1_range));
color_idx = 1;

for k1 = k1_range
    for h = h_range
        for h1 = h1_range
            % --- 几何参数计算（公式8的逆用）---
            d = h / gamma_target;                          % 垂直间距 m
            a = (a_hat_target / sqrt(1 - a_hat_target^2)) * h1;  % 水平距离 m
            L_norm = sqrt(a^2 + h1^2);                     % 归一化长度
            delta = delta_hat_target * L_norm;             % 预压缩量 m
            
            % --- 刚度计算（公式8）---
            k2 = k1 / alpha_target;                        % 垂直弹簧刚度 N/m
            k3 = alpha1_target * k2;                        % 中间斜弹簧刚度 N/m
            
            % --- 实际无量纲参数（公式8验证）---
            alpha_actual    = k1 / k2;                      % α实际
            alpha1_actual   = k3 / k2;                      % α₁实际
            a_hat_actual    = a / L_norm;                   % â实际
            gamma_actual    = h / d;                         % γ实际
            delta_hat_actual = delta / L_norm;               % δ̂实际
            
            % --- 计算ρ（公式8）---
            rho = (1 - a_hat_actual^2) / (gamma_actual - 1)^2;
            
            % --- 计算δ̂₁和δ̂₂（公式9-10）---
            term_a = sqrt(1 - a_hat_actual^2);
            term_rho = sqrt(rho);
            
            delta_hat1 = 1 - sqrt(1 + 2*term_a*term_rho + rho) + delta_hat_actual;
            delta_hat2 = 1 - sqrt(1 + 4*term_a*term_rho + 4*rho) + delta_hat_actual;
            
            % --- 误差计算 ---
            err_alpha  = abs(alpha_actual - alpha_target) / alpha_target * 100;
            err_alpha1 = abs(alpha1_actual - alpha1_target) / alpha1_target * 100;
            err_a_hat  = abs(a_hat_actual - a_hat_target) / a_hat_target * 100;
            err_gamma  = abs(gamma_actual - gamma_target) / gamma_target * 100;
            err_delta  = abs(delta_hat_actual - delta_hat_target) / delta_hat_target * 100;
            
            fprintf('%8.1f | %5.1f | %5.1f | %7.1f | %7.1f | %5.1f | %5.1f | %9.2f | %.3f |   %.3f   |   %.2f   |    %.3f     |   %.2f   | %.3f | %.3f | %.3f |   %.2f\n', ...
                k1, h*1000, h1*1000, k2, k3, a*1000, d*1000, delta*1000, rho, ...
                a_hat_actual, err_a_hat, gamma_actual, err_gamma, alpha_actual, alpha1_actual, delta_hat_actual, err_delta);
            
            % --- 计算刚度-位移关系（公式7-12）---
            % 定义位移范围（相对于平衡位置）
            % 平衡位置 x_e = √(1-â²) + √ρ（见原文第3页）
            x_e = sqrt(1 - a_hat_actual^2) + sqrt(rho);
            y_hat = linspace(-0.2, 0.2, 100);      % 无量纲相对位移
            x_hat = x_e + y_hat;                    % 绝对位移
            
            % 初始化刚度数组
            K_hat = zeros(size(y_hat));
            
            % 对每个位移点计算刚度
            for i = 1:length(x_hat)
                xi = x_hat(i);
                
                % --- 公式7：计算P参数 ---
                term_a = sqrt(1 - a_hat_actual^2);      % √(1-â²)
                term_rho = sqrt(rho);                    % √ρ
                
                P1 = term_a - xi;
                P2 = 1 - 2*term_a*xi + xi^2;
                P3 = 1 + delta_hat_actual;
                
                P4 = term_a + rho + 2*term_a*term_rho - xi;
                P5 = 1 + rho + 2*term_a*term_rho - 2*(term_a + rho + 2*term_a*term_rho)*xi + xi^2;
                P6 = sqrt(1 + 2*term_a*term_rho + rho) + delta_hat1;
                
                P7 = term_a + 2*term_rho - xi;
                P8 = 1 + 4*term_a*term_rho + 4*rho - 2*(term_a + 2*term_rho)*xi + xi^2;
                P9 = sqrt(1 + 4*term_a*term_rho + 4*rho) + delta_hat2;
                
                % --- 公式12：计算dP项 ---
                dP1 = -1;
                dP4 = -1;
                dP7 = -1;
                
                dP2 = -2*term_a + 2*xi;
                dP5 = -2*(term_a + rho + 2*term_a*term_rho) + 2*xi;
                dP8 = -2*(term_a + 2*term_rho) + 2*xi;
                
                % --- 公式12：计算dN项（严格按照原文形式）---
                dN1 = -2*alpha_actual * (1 - P3 * P2^(-1/2)) * dP1 ...
                      - alpha_actual * P1 * P2^(-3/2) * P3 * dP2;
                
                dN3 = -2*alpha1_actual * (1 - P6 * P5^(-1/2)) * dP4 ...
                      - alpha1_actual * P4 * P5^(-3/2) * P6 * dP5;
                
                dN5 = -2*alpha_actual * (1 - P9 * P8^(-1/2)) * dP7 ...
                      - alpha_actual * P7 * P8^(-3/2) * P9 * dP8;
                
                % --- 公式11：总刚度 ---
                K_hat(i) = 1 + dN1 + dN3 + dN5;
            end
            
            % 绘图
            plot(y_hat, K_hat, 'Color', colors(color_idx,:), 'LineWidth', 1);
            hold on;
        end
    end
    color_idx = color_idx + 1;
end

%% 图形设置
xlabel('无量纲相对位移 \^y', 'FontSize', 12, 'FontName', '宋体');
ylabel('无量纲刚度 \^K', 'FontSize', 12, 'FontName', '宋体');
title('刚度-位移关系曲线 (\^K vs \^y) - 严格按原文公式7-12', 'FontSize', 14, 'FontName', '宋体');
grid on;
xlim([-0.2, 0.2]);
ylim([-0.5, 2]);

% 添加参考线
plot([-0.2, 0.2], [0, 0], 'k--', 'LineWidth', 0.5, 'Color', [0.5 0.5 0.5]);  % 零刚度线
plot([0, 0], [-0.5, 2], 'k--', 'LineWidth', 0.5, 'Color', [0.5 0.5 0.5]);    % 平衡位置线

% 添加图例说明
text(0.15, 1.8, 'k1 = 100-900 N/m', 'FontSize', 10);
text(0.15, 1.6, 'h = 100-300 mm', 'FontSize', 10);
text(0.15, 1.4, 'h1 = 140-400 mm', 'FontSize', 10);

hold off;

fprintf('========================================================================================================================================================\n');
fprintf('已绘制所有参数组合的刚度-位移曲线，共 %d 条曲线\n', length(k1_range) * length(h_range) * length(h1_range));