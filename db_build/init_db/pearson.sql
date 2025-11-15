-- Enable PL/Python extension
CREATE EXTENSION IF NOT EXISTS plpython3u;

-- Create Pearson correlation function using scipy
CREATE OR REPLACE FUNCTION public.stat_pearson_correlation(x FLOAT[], y FLOAT[])
RETURNS FLOAT
AS $$
    from scipy.stats import pearsonr
    
    if len(x) != len(y) or len(x) < 2:
        return None
    
    correlation, p_value = pearsonr(x, y)
    return float(correlation)
$$ LANGUAGE plpython3u IMMUTABLE;

-- Add comment to the function
COMMENT ON FUNCTION public.stat_pearson_correlation(FLOAT[], FLOAT[]) IS 
'Calculates Pearson correlation coefficient between two float arrays. Returns NULL if arrays are different lengths or have fewer than 2 elements. Returns correlation value between -1 (perfect negative) and 1 (perfect positive).';


-- Create function that returns both correlation and p-value
CREATE OR REPLACE FUNCTION public.stat_pearson_correlation_with_p(x FLOAT[], y FLOAT[])
RETURNS TABLE(correlation FLOAT, p_value FLOAT)
AS $$
    from scipy.stats import pearsonr
    
    if len(x) != len(y) or len(x) < 2:
        return [(None, None)]
    
    corr, pval = pearsonr(x, y)
    return [(float(corr), float(pval))]
$$ LANGUAGE plpython3u IMMUTABLE;

-- Add comment to the function
COMMENT ON FUNCTION public.stat_pearson_correlation_with_p(FLOAT[], FLOAT[]) IS 
'Calculates Pearson correlation coefficient and p-value between two float arrays. Returns a table with correlation and p_value columns. P-value tests the null hypothesis that the correlation is zero.';


-- Grant execute permissions to public
GRANT EXECUTE ON FUNCTION public.stat_pearson_correlation(FLOAT[], FLOAT[]) TO PUBLIC;
GRANT EXECUTE ON FUNCTION public.stat_pearson_correlation_with_p(FLOAT[], FLOAT[]) TO PUBLIC;

-- Test the functions
DO $$
DECLARE
    result FLOAT;
    test_result RECORD;
BEGIN
    -- Test basic correlation
    result := public.stat_pearson_correlation(
        ARRAY[1.0, 2.0, 3.0, 4.0, 5.0],
        ARRAY[2.0, 4.0, 5.0, 4.0, 5.0]
    );
    RAISE NOTICE 'Test correlation result: %', result;
    
    -- Test correlation with p-value
    SELECT * INTO test_result FROM public.stat_pearson_correlation_with_p(
        ARRAY[1.0, 2.0, 3.0, 4.0, 5.0],
        ARRAY[2.0, 4.0, 5.0, 4.0, 5.0]
    );
    RAISE NOTICE 'Correlation: %, P-value: %', test_result.correlation, test_result.p_value;
END $$;