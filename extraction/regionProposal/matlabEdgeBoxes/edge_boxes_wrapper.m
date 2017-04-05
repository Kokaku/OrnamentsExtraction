function all_boxes = edge_boxes_wrapper(image_filenames_txt, output_filename, resize, alpha, beta, minScore, maxBoxes, numThreads)

%% load pre-trained edge detection model and set opts (see edgesDemo.m)
model=load('models/forest/modelBsds'); model=model.model;
model.opts.multiscale=0; model.opts.sharpen=2; model.opts.nThreads=4;


%% set up opts for edgeBoxes (see edgeBoxes.m)
opts = edgeBoxes;
opts.alpha = alpha;%.65;     	% step size of sliding window search
opts.beta  = beta;%.75;     	% nms threshold for object proposals
opts.minScore = minScore;%.01;  % min score of boxes to detect
opts.maxBoxes = maxBoxes;%1e4;  % max number of boxes to detect

%% process all images and detect Edge Box bounding box proposals (see edgeBoxes.m)
all_boxes = {};
image_filenames = textread(image_filenames_txt, '%s');
parpool(numThreads)
parfor i=1:length(image_filenames)
	[im,map] = imread(image_filenames{i});
	imSize = size(im);

	ratio = 1
	if max(imSize) == 1
		all_boxes{i} = []
	else
		if resize > 0
			ratio = resize/max(imSize);
			im = imresize(im, ratio);
		end

		if isempty(map)
	    	map = [[0 0 0]; [1 1 1]];
		end
		s = size(imSize);
		if s(2) == 2
			im = ind2rgb(im,map);
		end

	    boxes = edgeBoxes(im,model,opts);
	    all_boxes{i} = boxes/ratio
	end
end
%delete(gcp)

if nargin > 1
    all_boxes
    save(output_filename, 'all_boxes', '-v7');
end
