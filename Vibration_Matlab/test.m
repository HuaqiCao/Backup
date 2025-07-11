function f0 = calc_natural_frequency(m, k)
    % 计算一阶固有频率 f0（Hz）
    % m - 质量 (kg)
    % k - 刚度 (N/m)
    
    if m <= 0 || k <= 0
        error('质量和刚度必须为正数！');
    end

    % 固有频率计算公式：f0 = (1 / 2π) * sqrt(k / m)
    f0 = (1 / (2 * pi)) * sqrt(k / m);

    % 输出结果
    fprintf('当质量 m = %.3f kg，刚度 k = %.3f N/m 时，固有频率 f0 = %.4f Hz\n', m, k, f0);
end
