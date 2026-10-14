"""Environmental context calculations. These metrics do not establish cause."""
from collections import deque
from datetime import datetime, timezone
import heapq
import math

import numpy as np
from scipy import ndimage


def accumulation(times, rates, timestamp, hours, bin_seconds=1800):
    """Use only complete bins before the observation; reject gaps and duplicates."""
    times = np.asarray(times, dtype='int64')
    if len(times) != len(rates) or np.any(np.diff(times) <= 0):
        raise ValueError('Rainfall timestamps must be unique and increasing')
    if hours * 3600 % bin_seconds:
        raise ValueError('Window must contain whole rainfall bins')
    instant = int(datetime.fromisoformat(timestamp.replace('Z','+00:00')).timestamp())
    end = instant // bin_seconds * bin_seconds
    start = end - hours*3600
    expected = np.arange(start,end,bin_seconds,dtype='int64')
    selected = (times >= start) & (times < end)
    if not np.array_equal(times[selected],expected):
        raise ValueError('Missing rainfall time bins in accumulation window')
    values = np.asarray(rates[selected], dtype='float64')
    valid = np.isfinite(values) & (values >= 0)
    total = np.sum(np.where(valid,values,0),axis=0)*(bin_seconds/3600)
    total[~valid.all(axis=0)] = np.nan
    iso = lambda epoch: datetime.fromtimestamp(epoch,timezone.utc).isoformat().replace('+00:00','Z')
    return total.astype('float32'), {'requested_end_utc': timestamp, 'start_inclusive_utc': iso(start),
        'end_exclusive_utc': iso(end), 'end_lag_seconds': instant-end,
        'hours':hours,'bin_count':len(expected),'bin_duration_seconds':bin_seconds,
        'units':'mm','complete_cell_fraction':float(valid.all(axis=0).mean())}


def terrain_derivatives(dem, resolution, relative_radius=510):
    valid = np.isfinite(dem)
    # y decreases as row increases on a north-up raster.
    row_gradient, dx = np.gradient(dem.astype('float64'),resolution)
    dy = -row_gradient
    gradient = np.hypot(dx,dy)
    slope = np.degrees(np.arctan(gradient))
    aspect = np.degrees(np.arctan2(-dx,-dy)) % 360
    aspect[gradient < 1e-8] = np.nan  # Flat terrain has no downslope aspect.
    laplacian = (np.gradient(dx,resolution,axis=1) - np.gradient(dy,resolution,axis=0))
    complete = ndimage.minimum_filter(valid.astype('uint8'),size=3,mode='constant',cval=0).astype(bool)
    mean = ndimage.uniform_filter(np.nan_to_num(dem).astype('float64'),3,mode='nearest')
    square = ndimage.uniform_filter(np.nan_to_num(dem).astype('float64')**2,3,mode='nearest')
    roughness = np.sqrt(np.maximum(0,square-mean**2))
    size = 2*round(relative_radius/resolution)+1
    count = ndimage.uniform_filter(valid.astype('float64'),size,mode='constant')
    local = ndimage.uniform_filter(np.nan_to_num(dem).astype('float64'),size,mode='constant')
    relative = dem - np.divide(local,count,out=np.full_like(local,np.nan),where=count>=1-1e-10)
    output = {'dem':dem.copy(),'slope':slope,'aspect':aspect,'curvature':laplacian,
              'roughness':roughness,'relative_elevation':relative}
    for name,array in output.items():
        array[~(valid if name=='dem' else complete)] = np.nan
        output[name] = array.astype('float32')
    return output


def flow_metrics(dem, resolution, slope, drainage_threshold_m2=1e6, epsilon=.001):
    """Priority-flood fill and D8 routing with deterministic parent routing on flats.

    The buffered domain has open boundary outlets. Contributing area is limited to
    this domain, so it can underestimate catchments entering through the boundary.
    """
    height,width = dem.shape
    valid = np.isfinite(dem); flat_valid=valid.ravel()
    filled = dem.astype('float64').ravel().copy()
    visited = ~valid.copy()
    boundary = valid & ~ndimage.binary_erosion(valid,structure=np.ones((3,3)),border_value=0)
    parent = np.full(dem.size,-1,dtype='int32')
    order = np.full(dem.size,-1,dtype='int32')
    seeds = np.flatnonzero(boundary.ravel())
    visited.ravel()[seeds]=True
    heap=[(float(filled[i]),int(i)) for i in seeds];heapq.heapify(heap)
    neighbors=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    sequence=0
    while heap:
        level,index=heapq.heappop(heap);order[index]=sequence;sequence+=1
        row,col=divmod(index,width)
        for dr,dc in neighbors:
            rr,cc=row+dr,col+dc
            if 0<=rr<height and 0<=cc<width and not visited[rr,cc]:
                visited[rr,cc]=True;other=rr*width+cc
                parent[other]=index;filled[other]=max(level,filled[other])
                heapq.heappush(heap,(float(filled[other]),other))
    receiver=parent.copy();best=np.zeros(dem.shape,dtype='float64')
    z=filled.reshape(dem.shape);ranks=order.reshape(dem.shape)
    # Vectorize steepest descent, requiring earlier flood rank to guarantee a DAG.
    for dr,dc in neighbors:
        rows=slice(max(0,-dr),min(height,height-dr));cols=slice(max(0,-dc),min(width,width-dc))
        other_rows=slice(max(0,dr),min(height,height+dr));other_cols=slice(max(0,dc),min(width,width+dc))
        drop=(z[rows,cols]-z[other_rows,other_cols])/(resolution*math.hypot(dr,dc))
        good=(valid[rows,cols]&valid[other_rows,other_cols]&
              (ranks[other_rows,other_cols]<ranks[rows,cols])&(drop>best[rows,cols]))
        rr,cc=np.mgrid[rows,cols]
        view=receiver.reshape(dem.shape)[rows,cols]
        view[good]=((rr+dr)*width+cc+dc)[good]
        best[rows,cols][good]=drop[good]
    # Boundary cells stay outlets; no invented catchment outside the downloaded domain.
    receiver[boundary.ravel()]=-1
    targets=receiver[receiver>=0]
    indegree=np.bincount(targets,minlength=dem.size).astype('int32')
    queue=deque(np.flatnonzero(flat_valid&(indegree==0)).tolist())
    count=flat_valid.astype('float64');processed=0
    while queue:
        index=queue.popleft();processed+=1;other=int(receiver[index])
        if other>=0:
            count[other]+=count[index];indegree[other]-=1
            if indegree[other]==0:queue.append(other)
    if processed!=int(valid.sum()):raise ValueError('Flow routing cycle or unvisited valid DEM cell')
    area=count.reshape(dem.shape)*resolution**2
    channel=valid&(area>=drainage_threshold_m2)
    distance=ndimage.distance_transform_edt(~channel,sampling=resolution) if channel.any() else np.full(dem.shape,np.nan)
    twi=np.log((area/resolution)/(np.tan(np.radians(slope))+epsilon))
    fill_depth=z-dem
    output={'flow_accumulation':area,'drainage_distance':distance,'twi':twi,'fill_depth':fill_depth}
    for name,array in output.items():
        array[~valid]=np.nan;output[name]=array.astype('float32')
    return output, {'processed_cells':processed,'outlet_count':int(boundary.sum()),
                    'outlet_contributing_area_m2':float(area[boundary].sum()),
                    'valid_domain_area_m2':int(valid.sum())*resolution**2,
                    'maximum_fill_depth_m':float(np.nanmax(fill_depth)),
                    'drainage_cell_count':int(channel.sum())}
